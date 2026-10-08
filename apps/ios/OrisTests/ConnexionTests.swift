import Foundation
import XCTest

@testable import Oris

private final class RecordingTransport: HTTPTransport, @unchecked Sendable {
    var last: URLRequest?

    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        last = request
        let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
        return (Data("{}".utf8), response)
    }
}

final class ConnexionTests: XCTestCase {
    func testAnAddressWithoutSchemeIsCompletedAndGarbageRefused() {
        XCTAssertEqual(Connexion.adresse("192.168.1.20:8000")?.absoluteString, "http://192.168.1.20:8000")
        XCTAssertEqual(Connexion.adresse(" http://mac.local:8000 ")?.absoluteString, "http://mac.local:8000")
        XCTAssertNil(Connexion.adresse(""))
        XCTAssertNil(Connexion.adresse("ftp://mac.local"))
    }

    func testTheTokenTravelsWithEveryRequest() async throws {
        let recorder = RecordingTransport()
        let transport = AuthorizingTransport(base: recorder, token: "oris_secret")
        _ = try await transport.send(URLRequest(url: URL(string: "http://api.test/patients")!))
        XCTAssertEqual(recorder.last?.value(forHTTPHeaderField: "Authorization"), "Bearer oris_secret")
    }

    func testTheDiagnosticNamesTheAddressAndTheCause() {
        let local = Connexion.pourquoi(URLError(.cannotConnectToHost), adresse: URL(string: "http://localhost:8000")!)
        XCTAssertTrue(local.contains("localhost"))
        XCTAssertTrue(local.contains("iPhone lui-même"))
        let muet = Connexion.pourquoi(URLError(.timedOut), adresse: URL(string: "http://10.0.0.7:8000")!)
        XCTAssertTrue(muet.contains("10.0.0.7:8000"))
        XCTAssertTrue(muet.contains("même Wi-Fi"))
        let refus = Connexion.pourquoi(APIError.httpStatus(401), adresse: URL(string: "http://10.0.0.7:8000")!)
        XCTAssertTrue(refus.contains("jeton"))
    }
}

extension ConnexionTests {
    /// Le 08/10/2026 : une adresse publique saisie sans « https:// » partait en clair,
    /// iOS la bloquait, et l'app annonçait « serveur injoignable » à tort.
    func testAPublicAddressTypedWithoutSchemeGoesOverHTTPS() {
        XCTAssertEqual(
            Connexion.adresse("51-159-130-158.nip.io/mobile")?.scheme, "https")
        XCTAssertEqual(Connexion.adresse("oris.exemple.fr")?.scheme, "https")
    }

    /// Le serveur du cabinet, lui, reste joignable en clair : c'est le réseau local.
    func testAMachineOnTheLocalNetworkKeepsPlainHTTP() {
        for locale in ["MacBook-Pro-3.local:8000", "localhost:8000", "192.168.1.20:8000",
                       "10.0.0.7:8000", "172.16.4.2:8000"] {
            XCTAssertEqual(Connexion.adresse(locale)?.scheme, "http", locale)
        }
    }

    /// Ce que le praticien écrit en entier n'est jamais réécrit.
    func testAnAddressTypedInFullIsLeftAlone() {
        XCTAssertEqual(Connexion.adresse("http://10.0.0.7:8000")?.scheme, "http")
        XCTAssertEqual(Connexion.adresse("https://oris.exemple.fr/mobile")?.path, "/mobile")
    }
}
