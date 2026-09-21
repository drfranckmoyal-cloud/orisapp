import SwiftUI

/// S04 — écoute active : symbole, chronomètre, activité vocale, Pause / Terminer.
struct ActiveListeningView: View {
    let patientName: String
    var visitKind: VisitKind = .consultation
    let controller: CaptureController
    let isOnline: Bool
    let missing: [String]?
    let errorText: String?
    let maxMinutes: Int
    let finish: (Bool) -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var pulse = false

    private var stateText: String {
        switch controller.phase {
        case .recording: "Écoute en cours"
        case .paused: "En pause — micro coupé"
        case .interrupted: "Interrompue par un appel ou Siri"
        case .microphoneLost: "Micro perdu"
        case .finishing: controller.pendingUploads > 0 ? "Envoi des derniers segments…" : "Oris prépare le dossier…"
        case .finished: "Oris prépare le dossier…"
        default: ""
        }
    }

    var body: some View {
        VStack(spacing: OrisSpacing.s16) {
            HStack {
                Text(patientName).font(.headline).foregroundStyle(OrisColor.deepGreen)
                Spacer()
                Label(
                    connectionText,
                    systemImage: controller.reconnecting || !isOnline ? "wifi.exclamationmark" : "wifi"
                )
                .font(.caption.bold())
                .foregroundStyle(controller.reconnecting || !isOnline ? OrisColor.warning : OrisColor.deepGreen)
            }

            banners

            Spacer()

            ZStack {
                Circle()
                    .fill(controller.phase == .recording ? OrisColor.orisGreen : OrisColor.white)
                    .frame(width: 140, height: 140)
                    .scaleEffect(pulse && controller.phase == .recording && !reduceMotion ? 1.06 : 1)
                    .animation(reduceMotion ? nil : .easeInOut(duration: 0.9).repeatForever(autoreverses: true), value: pulse)
                Image(systemName: symbol)
                    .font(.system(size: 52, weight: .semibold))
                    .foregroundStyle(controller.phase == .recording ? OrisColor.white : OrisColor.deepGreen)
            }
            .accessibilityHidden(true)
            .onAppear { pulse = true }

            Text(stateText)
                .font(.title2.bold())
                .foregroundStyle(controller.phase == .microphoneLost || controller.phase == .interrupted ? OrisColor.danger : OrisColor.deepGreen)
                .accessibilityAddTraits(.updatesFrequently)

            Text(formatDuration(controller.recordedMs))
                .font(.system(size: 48, weight: .semibold).monospacedDigit())
                .foregroundStyle(OrisColor.deepGreen)
                .accessibilityLabel("Durée écoutée \(formatDuration(controller.recordedMs))")

            ProgressView(value: controller.level)
                .tint(OrisColor.brightGreen)
                .frame(width: 200)
                .accessibilityHidden(true)

            Spacer()

            DerouleView(kind: visitKind, compact: true)
                .padding(.horizontal, OrisSpacing.s8)

            actions
        }
        .padding(OrisSpacing.s16)
        .navigationBarTitleDisplayMode(.inline)
    }

    private var symbol: String {
        switch controller.phase {
        case .recording: "waveform"
        case .interrupted, .microphoneLost: "mic.slash"
        case .finishing, .finished: "doc.text"
        default: "pause.fill"
        }
    }

    private var connectionText: String {
        if !isOnline || controller.reconnecting {
            return controller.pendingUploads > 0 ? "Hors connexion · \(controller.pendingUploads) en attente" : "Hors connexion"
        }
        return "Connecté"
    }

    @ViewBuilder
    private var banners: some View {
        if controller.phase == .microphoneLost || controller.phase == .interrupted {
            Banner(text: "Aucun son n’est capté. Touchez Reprendre quand la consultation reprend : l’interruption sera signalée dans le dossier.", critical: true)
        }
        if controller.lostUploads > 0 {
            Banner(text: "\(controller.lostUploads) segment(s) audio refusé(s) : ils seront signalés comme manquants.", critical: true)
        }
        if controller.maxDurationReached {
            Banner(text: "Durée maximale de \(maxMinutes) minutes atteinte : l’écoute est en pause. Terminez la consultation.", critical: false)
        } else if controller.warnDurationReached {
            Banner(text: "L’écoute approche de la durée maximale (\(maxMinutes) minutes).", critical: false)
        }
        if let errorText {
            Banner(text: errorText, critical: true)
        }
    }

    @ViewBuilder
    private var actions: some View {
        if controller.phase == .finishing || controller.phase == .finished {
            VStack(spacing: OrisSpacing.s12) {
                ProgressView()
                if missing != nil || (controller.reconnecting && controller.pendingUploads > 0) {
                    Text(missing != nil
                         ? "\(missing?.count ?? 0) segment(s) ne sont pas arrivés au serveur."
                         : "Connexion absente : les derniers segments attendent. Ils restent chiffrés sur l’iPhone.")
                        .font(.footnote)
                        .multilineTextAlignment(.center)
                    Button("Terminer malgré tout") { finish(true) }
                        .buttonStyle(.bordered)
                    Text("La partie manquante sera signalée par une alerte critique.").font(.caption)
                }
            }
        } else {
            HStack(spacing: OrisSpacing.s16) {
                if controller.phase == .recording {
                    Button {
                        Task { await controller.pause() }
                    } label: {
                        Text("Pause").font(.title3.bold()).frame(maxWidth: .infinity, minHeight: 56)
                    }
                    .buttonStyle(.bordered)
                } else {
                    Button {
                        Task { await controller.resume() }
                    } label: {
                        Text("Reprendre").font(.title3.bold()).frame(maxWidth: .infinity, minHeight: 56)
                    }
                    .buttonStyle(.bordered)
                    .disabled(controller.maxDurationReached)
                }
                Button {
                    finish(false)
                } label: {
                    Text("Terminer").font(.title3.bold()).frame(maxWidth: .infinity, minHeight: 56)
                }
                .buttonStyle(.borderedProminent)
                .tint(OrisColor.deepGreen)
            }
            .tint(OrisColor.deepGreen)
        }
    }
}

private struct Banner: View {
    let text: String
    let critical: Bool

    var body: some View {
        Label(text, systemImage: critical ? "exclamationmark.octagon.fill" : "exclamationmark.triangle.fill")
            .font(.footnote)
            .foregroundStyle(critical ? OrisColor.danger : OrisColor.warning)
            .padding(OrisSpacing.s12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(OrisColor.white, in: RoundedRectangle(cornerRadius: 12))
    }
}
