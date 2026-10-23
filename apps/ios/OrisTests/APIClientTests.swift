import Foundation
import XCTest

@testable import Oris

private struct StubTransport: HTTPTransport {
    let status: Int
    let body: String
    /// Ce que rendent les routes autres que `/health`, quand l'essai en a besoin.
    var listeBody: String?

    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!
        let chemin = request.url?.path ?? ""
        let corps = chemin.hasSuffix("/health") ? body : (listeBody ?? body)
        return (Data(corps.utf8), response)
    }
}

/// Un serveur en bonne santé qui refuse pourtant cet iPhone : c'est ce que vit une app
/// dont le jeton est absent ou faux — `/health` ne demande rien, le reste exige le jeton.
private struct SanteOkMaisRefuseTransport: HTTPTransport {
    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        let chemin = request.url?.path ?? ""
        let refus = !chemin.hasSuffix("/health")
        let response = HTTPURLResponse(url: request.url!, statusCode: refus ? 403 : 200,
                                       httpVersion: nil, headerFields: nil)!
        let corps = refus ? #"{"code":"INVALID_TOKEN","subject_id":null,"details":[]}"# : healthBody
        return (Data(corps.utf8), response)
    }
}

private struct FailingTransport: HTTPTransport {
    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        throw URLError(.cannotConnectToHost)
    }
}

private let healthBody = #"""
{"status":"ok","service":"oris-api","version":"0.1.0","environment":"local",
 "providers":{"speech_to_text":"mock","clinical_extraction":"mock",
 "document_generation":"mock","clinical_validation":"mock"}}
"""#

final class APIClientTests: XCTestCase {
    private let baseURL = URL(string: "http://api.test")!

    func testHealthDecodesResponse() async throws {
        let client = APIClient(baseURL: baseURL, transport: StubTransport(status: 200, body: healthBody))
        let health = try await client.health()
        XCTAssertEqual(health.version, "0.1.0")
        XCTAssertTrue(health.providers.allMock)
    }

    func testHTTPErrorIsReported() async {
        let client = APIClient(baseURL: baseURL, transport: StubTransport(status: 503, body: "{}"))
        do {
            _ = try await client.health()
            XCTFail("503 attendu")
        } catch {
            XCTAssertEqual(error as? APIError, .httpStatus(503))
        }
    }

    @MainActor
    func testHomeShowsUnreachableWhenServerIsDown() async {
        let model = HomeViewModel(client: APIClient(baseURL: baseURL, transport: FailingTransport()))
        await model.refresh()
        XCTAssertEqual(model.serverState, .unreachable)
    }

    @MainActor
    func testHomeShowsReachableServer() async throws {
        let transport = StubTransport(status: 200, body: healthBody, listeBody: "[]")
        let model = HomeViewModel(client: APIClient(baseURL: baseURL, transport: transport))
        await model.refresh()
        guard case .reachable(let health) = model.serverState else {
            return XCTFail("serveur joignable attendu")
        }
        XCTAssertEqual(health.service, "oris-api")
    }

    /// 24/10/2026 : pendant deux semaines, l'app a annoncé « Serveur Oris connecté » alors
    /// qu'elle était refusée à chaque lecture — le contrôle ne portait que sur `/health`,
    /// qui ne demande pas de jeton. Franck a cherché du côté du réseau un problème qui
    /// était dans ses réglages. Un serveur qui répond mais qui refuse, ça se dit.
    @MainActor
    func testHomeSaysTheServerAnswersButRefusesThisPhone() async {
        let model = HomeViewModel(client: APIClient(baseURL: baseURL, transport: SanteOkMaisRefuseTransport()))
        await model.refresh()
        guard case .refuse(let raison) = model.serverState else {
            return XCTFail("refus attendu, pas « connecté » ni « injoignable »")
        }
        XCTAssertTrue(raison.contains("jeton"), "la raison nomme le jeton : « \(raison) »")
        XCTAssertTrue(model.aRelire.isEmpty)
    }
}
