import Foundation
import XCTest

@testable import Oris

private struct StubTransport: HTTPTransport {
    let status: Int
    let body: String

    func send(_ request: URLRequest) async throws -> (Data, URLResponse) {
        let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!
        return (Data(body.utf8), response)
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
        let transport = StubTransport(status: 200, body: healthBody)
        let model = HomeViewModel(client: APIClient(baseURL: baseURL, transport: transport))
        await model.refresh()
        guard case .reachable(let health) = model.serverState else {
            return XCTFail("serveur joignable attendu")
        }
        XCTAssertEqual(health.service, "oris-api")
    }
}
