import Foundation

/// Format audio attendu par l'API (identique au web) : PCM 16 bits signé, 16 kHz, mono.
enum AudioFormat {
    static let contentType = "audio/pcm;rate=16000;channels=1;encoding=s16le"
    static let sampleRate = 16_000
    static let samplesPerMs = 16
    static let chunkSamples = 32_000 // 2 s
}

/// Rééchantillonneur par moyenne, avec état : les blocs successifs se raccordent sans perte.
struct Resampler: Sendable {
    let inputRate: Double
    private let ratio: Double
    private var carry: [Float] = []
    private var position: Double = 0

    init(inputRate: Double, outputRate: Double = Double(AudioFormat.sampleRate)) {
        self.inputRate = inputRate
        self.ratio = max(1, inputRate / outputRate)
    }

    mutating func process(_ input: [Float]) -> [Float] {
        if ratio == 1 { return input }
        let samples = carry + input
        var output: [Float] = []
        output.reserveCapacity(Int(Double(samples.count) / ratio) + 1)
        var cursor = position
        while cursor + ratio <= Double(samples.count) {
            let start = Int(cursor)
            let end = Int(cursor + ratio)
            var sum: Float = 0
            for index in start..<end { sum += samples[index] }
            output.append(sum / Float(max(1, end - start)))
            cursor += ratio
        }
        let consumed = Int(cursor)
        carry = Array(samples[consumed...])
        position = cursor - Double(consumed)
        return output
    }
}

enum PCM {
    static func toInt16(_ samples: [Float]) -> [Int16] {
        samples.map { sample in
            let clamped = min(1, max(-1, sample))
            return clamped < 0 ? Int16(clamped * 32768) : Int16(clamped * 32767)
        }
    }

    /// Octets little-endian, quel que soit le processeur.
    static func bytes(_ samples: [Int16]) -> Data {
        var data = Data(capacity: samples.count * 2)
        for sample in samples {
            let value = UInt16(bitPattern: sample.littleEndian)
            data.append(UInt8(value & 0xFF))
            data.append(UInt8(value >> 8))
        }
        return data
    }

    static func samples(from data: Data) -> [Int16] {
        stride(from: 0, to: data.count - data.count % 2, by: 2).map { offset in
            let low = UInt16(data[data.startIndex + offset])
            let high = UInt16(data[data.startIndex + offset + 1])
            return Int16(bitPattern: low | (high << 8))
        }
    }

    /// Niveau sonore 0…1 pour l'indicateur d'activité vocale.
    static func level(_ samples: [Float]) -> Double {
        guard !samples.isEmpty else { return 0 }
        let meanSquare = samples.reduce(Float(0)) { $0 + $1 * $1 } / Float(samples.count)
        return min(1, Double(sqrt(meanSquare)) * 4)
    }
}

/// Segment numéroté et horodaté en temps écouté (pauses exclues).
struct PcmChunk: Sendable, Equatable {
    let sequence: Int
    let timestampMs: Int
    let durationMs: Int
    let samples: [Int16]

    var data: Data { PCM.bytes(samples) }
}

struct Chunker: Sendable {
    private var buffer: [Int16] = []
    private(set) var nextSequence: Int
    private var sampleOffset: Int
    let chunkSamples: Int

    init(chunkSamples: Int = AudioFormat.chunkSamples, startSequence: Int = 0, startTimestampMs: Int = 0) {
        self.chunkSamples = chunkSamples
        self.nextSequence = startSequence
        self.sampleOffset = startTimestampMs * AudioFormat.samplesPerMs
        buffer.reserveCapacity(chunkSamples)
    }

    var recordedMs: Int { (sampleOffset + buffer.count) / AudioFormat.samplesPerMs }
    var lastSequence: Int { nextSequence - 1 }

    mutating func push(_ samples: [Int16]) -> [PcmChunk] {
        var chunks: [PcmChunk] = []
        var index = samples.startIndex
        while index < samples.endIndex {
            let take = min(chunkSamples - buffer.count, samples.endIndex - index)
            buffer.append(contentsOf: samples[index..<(index + take)])
            index += take
            if buffer.count == chunkSamples {
                chunks.append(emit())
            }
        }
        return chunks
    }

    mutating func flush() -> PcmChunk? {
        buffer.isEmpty ? nil : emit()
    }

    private mutating func emit() -> PcmChunk {
        let chunk = PcmChunk(
            sequence: nextSequence,
            timestampMs: sampleOffset / AudioFormat.samplesPerMs,
            durationMs: Int((Double(buffer.count) / Double(AudioFormat.samplesPerMs)).rounded()),
            samples: buffer
        )
        nextSequence += 1
        sampleOffset += buffer.count
        buffer.removeAll(keepingCapacity: true)
        return chunk
    }
}
