import Foundation
import Observation

@MainActor
@Observable
final class ConsultationsViewModel {
    enum State: Equatable {
        case loading
        case failed
        case loaded([EncounterSummary])
    }

    private(set) var state: State = .loading
    private let client: APIClient

    init(client: APIClient) {
        self.client = client
    }

    func refresh() async {
        do {
            state = .loaded(try await client.encounters())
        } catch {
            state = .failed
        }
    }
}

@MainActor
@Observable
final class ConsultationDetailViewModel {
    struct Content: Equatable {
        let encounter: EncounterSummary
        let documents: [DocumentDetail]
        /// Absent quand la transcription a échoué : la consultation existe quand même,
        /// et l'écran doit dire pourquoi il n'y a pas de compte rendu.
        let clinicalObject: ClinicalEncounter?

        var warnings: [EncounterWarning] { clinicalObject?.warnings ?? [] }
        var facts: [ClinicalFact] { clinicalObject?.facts ?? [] }

        var criticalWarnings: [EncounterWarning] {
            warnings.filter { $0.severity == .critical }
        }

        /// Points « À vérifier » : alertes de la consultation et problèmes des documents.
        var reviewItemCount: Int {
            warnings.count + documents.reduce(0) { $0 + $1.validationIssues.count }
        }
    }

    enum State: Equatable {
        case loading
        case failed
        case loaded(Content)
    }

    private(set) var state: State = .loading
    let encounterId: String
    private let client: APIClient

    init(encounterId: String, client: APIClient) {
        self.encounterId = encounterId
        self.client = client
    }

    func refresh() async {
        do {
            async let encounter = client.encounter(id: encounterId)
            async let documents = client.documents(encounterId: encounterId)
            async let object = try? client.clinicalObject(encounterId: encounterId)
            state = .loaded(Content(encounter: try await encounter, documents: try await documents, clinicalObject: await object))
        } catch {
            state = .failed
        }
    }
}
