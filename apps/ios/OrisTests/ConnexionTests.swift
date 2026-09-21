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
