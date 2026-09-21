import SwiftUI
import UIKit

/// S03 pré-écran puis S04 écoute active. L'état du micro et du réseau est toujours visible.
struct ListeningView: View {
    let client: APIClient
    let encounter: EncounterSummary
    let onClose: () -> Void

    @State private var config: ClientConfig?
    @State private var audio: AudioSessionState?
    @State private var controller: CaptureController?
    @State private var network = NetworkMonitor()
    @State private var patientInformed = false
    @State private var visitKind: VisitKind = .consultation
    @State private var useTestTone = false
    @State private var missing: [String]?
    @State private var errorText: String?
    @State private var finishedEncounterId: String?
    @State private var loaded = false

    private var interruptedByRelaunch: Bool {
        controller == nil && [.recording, .paused].contains(encounter.status)
    }

    var body: some View {
        Group {
            if !loaded {
                ProgressView("Chargement…").tint(Teinte.accent)
            } else if let controller, controller.phase != .ready, controller.phase != .starting, controller.phase != .error {
                ActiveListeningView(
                    patientName: encounter.patient.displayName,
                    visitKind: visitKind,
                    controller: controller,
                    isOnline: network.isOnline,
                    missing: missing,
                    errorText: errorText,
                    maxMinutes: config?.maxSessionMinutes ?? 90,
                    finish: { acceptGaps in Task { await finish(acceptGaps: acceptGaps) } }
                )
            } else if interruptedByRelaunch {
                relaunchView
            } else {
                preScreen
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Teinte.fond.ignoresSafeArea())
        .tint(Teinte.accent)
        // Pendant l'écoute, rien ne doit pouvoir faire quitter l'écran par erreur.
        .toolbar(.hidden, for: .tabBar)
        .navigationBarBackButtonHidden(controller.map { [.recording, .paused, .interrupted, .microphoneLost, .finishing].contains($0.phase) } ?? false)
        .navigationDestination(item: $finishedEncounterId) { id in
            ConsultationDetailView(model: ConsultationDetailViewModel(encounterId: id, client: client))
                .toolbar {
                    ToolbarItem(placement: .confirmationAction) { Button("Terminé", action: onClose) }
                }
        }
        .task { await load() }
        .onChange(of: controller?.phase) { _, phase in
            // Écran allumé pendant l'écoute ; l'écoute continue aussi écran verrouillé.
            UIApplication.shared.isIdleTimerDisabled = phase == .recording
        }
        .onDisappear { UIApplication.shared.isIdleTimerDisabled = false }
    }

    // MARK: Pré-écran

    private var preScreen: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: OrisSpacing.s24) {
                HStack(spacing: OrisSpacing.s12) {
                    Vignette(initiales: encounter.patient.initiales, taille: 46)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("AVANT L’ÉCOUTE")
                            .font(Police.interface(11.5, .bold, relativeTo: .caption))
                            .tracking(1.1)
                            .foregroundStyle(Teinte.encreTresDouce)
                        NomPatient(patient: encounter.patient, taille: 22)
                    }
                }

                // Consultation ou acte : fixe le modèle de compte rendu et le déroulé.
                ChoixSeance(choix: $visitKind)
                    .disabled(controller?.phase == .starting)

                DerouleView(kind: visitKind)
                    .carte(fond: Teinte.surface2)

                VStack(alignment: .leading, spacing: OrisSpacing.s12) {
                    StatusLine(
                        icon: "mic",
                        text: useTestTone ? "Son de test (sans micro)" : microphoneText,
                        tone: MicrophoneInput.permission == .denied && !useTestTone ? .critical : .normal
                    )
                    StatusLine(
                        icon: network.isOnline ? "wifi" : "wifi.slash",
                        text: network.isOnline ? "Connexion disponible" : "Hors connexion",
                        tone: network.isOnline ? .normal : .warning
                    )
                }

                VStack(spacing: OrisSpacing.s12) {
                    if config?.testAudioSourceEnabled == true {
                        Toggle("Son de test, sans micro (développement)", isOn: $useTestTone)
                    }
                    if config?.patientInformationMode != "none" {
                        Toggle("Le patient a été informé de l’enregistrement de la consultation.", isOn: $patientInformed)
                    }
                }
                .font(Police.interface(15, .semibold))
                .foregroundStyle(Teinte.encre)
                .tint(Teinte.accent)
                .carte()

                if let code = controller?.errorCode {
                    VStack(alignment: .leading, spacing: OrisSpacing.s8) {
                        Text(Self.message(for: code)).font(Police.note).foregroundStyle(Teinte.alerte)
                        if code == CaptureFailure.permissionDenied.rawValue {
                            Button("Ouvrir les Réglages") {
                                if let url = URL(string: UIApplication.openSettingsURLString) {
                                    UIApplication.shared.open(url)
                                }
                            }
                        }
                    }
                }

                Button {
                    Task { await start() }
                } label: {
                    Label(controller?.phase == .starting ? "Démarrage…" : "Commencer l’écoute", systemImage: "waveform")
                }
                .buttonStyle(BoutonPrincipal())
                .disabled(controller?.phase == .starting || (config?.patientInformationMode != "none" && !patientInformed))
            }
            .padding(.horizontal, OrisSpacing.s16)
            .padding(.bottom, OrisSpacing.s32)
        }
        .scrollContentBackground(.hidden)
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var microphoneText: String {
        switch MicrophoneInput.permission {
        case .granted: "Micro autorisé"
        case .denied: "Micro refusé — à autoriser dans Réglages"
        case .undetermined: "Autorisation du micro demandée au démarrage"
        }
    }

    // MARK: Reprise après fermeture de l'app

    private var relaunchView: some View {
        VStack(alignment: .leading, spacing: OrisSpacing.s16) {
            NomPatient(patient: encounter.patient, taille: 22)
            Label(
                encounter.status == .recording
                    ? "L’écoute a été interrompue (app fermée). La partie non captée sera signalée comme manquante."
                    : "L’écoute était en pause quand l’app a été fermée.",
                systemImage: "exclamationmark.octagon.fill"
            )
            .font(Police.interface(15, .semibold))
            .foregroundStyle(Teinte.alerte)
            .carte(fond: Teinte.alerteDouce)
            if let audio {
                Text("Audio déjà reçu : \(formatDuration(audio.receivedDurationMs)).")
                    .font(Police.note).foregroundStyle(Teinte.encreDouce)
            }
            if config?.testAudioSourceEnabled == true {
                Toggle("Son de test, sans micro (développement)", isOn: $useTestTone)
            }
            Button {
                Task { await resumeAfterRelaunch() }
            } label: {
                Text("Reprendre l’écoute")
            }
            .buttonStyle(BoutonPrincipal())
            Button("Terminer la consultation") {
                Task { await finishAfterRelaunch() }
            }
            .buttonStyle(BoutonSecondaire())
            if let errorText {
                Text(errorText).font(Police.note).foregroundStyle(Teinte.alerte)
            }
            Spacer()
        }
        .padding(OrisSpacing.s16)
    }

    // MARK: Actions

    private func load() async {
        defer { loaded = true }
        config = try? await client.clientConfig()
        audio = try? await client.audioState(encounterId: encounter.id)
    }

    private func start() async {
        do {
            let controller = try self.controller ?? CaptureEnvironment.makeController(
                client: client, encounterId: encounter.id, useTestTone: useTestTone, config: config,
                visitKind: visitKind
            )
            self.controller = controller
            connectNetwork(controller)
            await controller.start(patientInformed: patientInformed)
        } catch {
            errorText = "Stockage local sécurisé indisponible : écoute impossible."
        }
    }

    private func resumeAfterRelaunch() async {
        do {
            let point = CaptureEnvironment.resumePoint(audio: audio, encounterId: encounter.id)
            let controller = try CaptureEnvironment.makeController(
                client: client, encounterId: encounter.id, useTestTone: useTestTone, config: config, resumeFrom: point
            )
            self.controller = controller
            connectNetwork(controller)
            let interruption = audio?.lastReceivedAt.flatMap(Self.parseDate).map { Int(Date().timeIntervalSince($0) * 1000) }
            await controller.resumeAfterRelaunch(interruptionMs: interruption, wasPaused: encounter.status == .paused)
        } catch {
            errorText = "Stockage local sécurisé indisponible : écoute impossible."
        }
    }

    private func finishAfterRelaunch() async {
        do {
            let point = CaptureEnvironment.resumePoint(audio: audio, encounterId: encounter.id)
            let controller = try CaptureEnvironment.makeController(
                client: client, encounterId: encounter.id, useTestTone: useTestTone, config: config, resumeFrom: point
            )
            _ = await controller.uploader.restorePending()
            if encounter.status == .recording {
                await controller.uploader.enqueue(.gap(reason: .appTerminated, durationMs: nil))
            }
            self.controller = controller
            connectNetwork(controller)
            await finish(acceptGaps: false)
        } catch {
            errorText = "Stockage local sécurisé indisponible."
        }
    }

    private func finish(acceptGaps: Bool) async {
        guard let controller else { return }
        errorText = nil
        do {
            switch try await controller.finish(acceptGaps: acceptGaps) {
            case .finished:
                finishedEncounterId = encounter.id
            case .chunksMissing(let sequences):
                missing = sequences
            }
        } catch {
            errorText = Self.message(for: (error as? APIError)?.code ?? "FINISH_FAILED")
        }
    }

    private func connectNetwork(_ controller: CaptureController) {
        network.onReconnect = { [controller] in
            Task { await controller.uploader.wake() }
        }
    }

    static func parseDate(_ value: String) -> Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: value) ?? ISO8601DateFormatter().date(from: value)
    }

    static func message(for code: String) -> String {
        switch code {
        case "permission_denied": "L’accès au micro a été refusé. Autorisez Oris dans Réglages › Confidentialité › Micro."
        case "no_microphone": "Aucun micro disponible."
        case "capture_failed": "La capture audio n’a pas pu démarrer."
        case "microphone_lost": "Le micro a été coupé. La partie non captée sera signalée."
        case "PATIENT_INFORMATION_REQUIRED": "Confirmez d’abord que le patient a été informé."
        case "LOCAL_STORAGE_FAILED": "Écriture locale impossible : une partie de l’audio sera signalée comme manquante."
        default: "Action impossible (\(code))."
        }
    }
}

func formatDuration(_ ms: Int) -> String {
    let seconds = ms / 1000
    let hours = seconds / 3600
    let minutes = (seconds % 3600) / 60
    return hours > 0
        ? String(format: "%d:%02d:%02d", hours, minutes, seconds % 60)
        : String(format: "%02d:%02d", minutes, seconds % 60)
}

struct StatusLine: View {
    enum Tone { case normal, warning, critical }

    let icon: String
    let text: String
    var tone: Tone = .normal

    var body: some View {
        Label(text, systemImage: icon)
            .font(Police.interface(14.5, .semibold))
            .foregroundStyle(tone == .critical ? Teinte.alerte : tone == .warning ? Teinte.attention : Teinte.accent)
            .carte(rembourrage: OrisSpacing.s12, fond: tone == .critical ? Teinte.alerteDouce : tone == .warning ? Teinte.attentionDouce : Teinte.surface)
            .accessibilityElement(children: .combine)
    }
}

/// Consultation ou acte : deux grandes pilules, comme les filtres du site.
struct ChoixSeance: View {
    @Binding var choix: VisitKind

    var body: some View {
        HStack(spacing: 4) {
            ForEach(VisitKind.allCases) { kind in
                Button { choix = kind } label: {
                    Text(kind.label)
                        .font(Police.interface(15, kind == choix ? .heavy : .semibold))
                        .foregroundStyle(kind == choix ? .white : Teinte.encreDouce)
                        .frame(maxWidth: .infinity, minHeight: 42)
                        .background {
                            if kind == choix {
                                RoundedRectangle(cornerRadius: 10, style: .continuous).fill(Teinte.accent)
                            }
                        }
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(kind == choix ? .isSelected : [])
            }
        }
        .padding(4)
        .background(Teinte.surfaceDouce, in: RoundedRectangle(cornerRadius: 13, style: .continuous))
    }
}
