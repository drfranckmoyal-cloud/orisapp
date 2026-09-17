import Foundation

struct UploadStatus: Sendable, Equatable {
    var pending: Int
    var retrying: Bool
    var lastErrorCode: String?
    var lost: Int
}

/// File d'envoi ordonnée : un seul envoi à la fois, dans l'ordre de capture.
///
/// Un segment est d'abord écrit dans le tampon chiffré, puis envoyé ; il n'est
/// supprimé qu'après accusé de réception. Erreur temporaire : nouvel essai avec
/// attente croissante, sans limite tant que la session vit (spec §69). Erreur
/// définitive : segment déclaré perdu (le serveur signalera le trou).
actor Uploader {
    private let encounterId: String
    private let store: ChunkStore
    private let transport: any AudioTransporting
    private let backoff: [Duration]
    private let onStatus: @Sendable (UploadStatus) -> Void

    private var queue: [UploadItem] = []
    private var running = false
    private var stopped = false
    private var retrying = false
    private var lastErrorCode: String?
    private var lost = 0
    private var drainWaiters: [CheckedContinuation<Void, Never>] = []
    private var sleepTask: Task<Void, Never>?

    init(
        encounterId: String,
        store: ChunkStore,
        transport: any AudioTransporting,
        backoff: [Duration] = [.milliseconds(500), .seconds(1), .seconds(2), .seconds(4), .seconds(8)],
        onStatus: @escaping @Sendable (UploadStatus) -> Void = { _ in }
    ) {
        self.encounterId = encounterId
        self.store = store
        self.transport = transport
        self.backoff = backoff
        self.onStatus = onStatus
    }

    var status: UploadStatus {
        UploadStatus(pending: queue.count, retrying: retrying, lastErrorCode: lastErrorCode, lost: lost)
    }

    /// Enregistre le segment chiffré puis le met en file.
    func enqueue(chunk: PcmChunk) throws {
        try store.save(chunk, encounterId: encounterId)
        append(.chunk(sequence: chunk.sequence))
    }

    func enqueue(_ item: UploadItem) {
        append(item)
    }

    /// Réouverture de l'app : les segments restés dans le tampon repartent en tête de file.
    func restorePending() -> [Int] {
        let queued = Set(queue.compactMap { item -> Int? in
            if case .chunk(let sequence) = item { return sequence }
            return nil
        })
        let restored = store.pendingSequences(encounterId: encounterId).filter { !queued.contains($0) }
        queue.insert(contentsOf: restored.map { UploadItem.chunk(sequence: $0) }, at: 0)
        publish()
        start()
        return restored
    }

    /// Le réseau est revenu : on n'attend pas la fin du délai en cours.
    func wake() {
        sleepTask?.cancel()
    }

    func waitUntilDrained() async {
        if queue.isEmpty { return }
        await withCheckedContinuation { drainWaiters.append($0) }
    }

    /// « Terminer malgré tout » : ce qui n'est pas parti est abandonné et effacé localement.
    func abandon() {
        for item in queue {
            if case .chunk(let sequence) = item {
                store.delete(encounterId: encounterId, sequence: sequence)
            }
        }
        queue.removeAll()
        stopped = true
        retrying = false
        sleepTask?.cancel()
        publish()
        resolveDrain()
    }

    #if DEBUG
    /// Tests : simule une app tuée (file perdue, tampon chiffré conservé).
    func abandonWithoutDeletingForTest() {
        queue.removeAll()
        stopped = true
        sleepTask?.cancel()
    }
    #endif

    private func append(_ item: UploadItem) {
        guard !stopped else { return }
        queue.append(item)
        publish()
        start()
    }

    private func start() {
        guard !running, !stopped else { return }
        running = true
        Task { await self.run() }
    }

    private func run() async {
        var attempt = 0
        while let item = queue.first, !stopped {
            var chunk: PcmChunk?
            var result: SendResult
            if case .chunk(let sequence) = item {
                chunk = try? store.load(encounterId: encounterId, sequence: sequence)
            }
            if case .chunk = item, chunk == nil {
                result = .failed(code: "LOCAL_CHUNK_UNREADABLE", retry: false)
            } else {
                result = await transport.send(item, chunk: chunk)
            }
            if stopped { break }
            switch result {
            case .ok:
                queue.removeFirst()
                if case .chunk(let sequence) = item {
                    store.delete(encounterId: encounterId, sequence: sequence)
                }
                attempt = 0
                retrying = false
                lastErrorCode = nil
            case .failed(let code, retry: true):
                retrying = true
                lastErrorCode = code
                publish()
                let delay = backoff[min(attempt, backoff.count - 1)]
                attempt += 1
                let task = Task { _ = try? await Task.sleep(for: delay) }
                sleepTask = task
                await task.value
                continue
            case .failed(let code, retry: false):
                queue.removeFirst()
                if case .chunk(let sequence) = item {
                    store.delete(encounterId: encounterId, sequence: sequence)
                }
                lost += 1
                lastErrorCode = code
                attempt = 0
            }
            publish()
        }
        running = false
        if queue.isEmpty { resolveDrain() }
    }

    private func resolveDrain() {
        let waiters = drainWaiters
        drainWaiters = []
        waiters.forEach { $0.resume() }
    }

    private func publish() {
        onStatus(status)
    }
}
