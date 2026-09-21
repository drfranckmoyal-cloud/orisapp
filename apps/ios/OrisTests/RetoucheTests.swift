import UIKit
import XCTest
@testable import Oris

@MainActor
final class RetoucheTests: XCTestCase {
    /// Une image de 200 × 100 : moitié gauche rouge, moitié droite bleue.
    private func image() -> UIImage {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        return UIGraphicsImageRenderer(size: CGSize(width: 200, height: 100), format: format).image { ctx in
            UIColor.red.setFill(); ctx.fill(CGRect(x: 0, y: 0, width: 100, height: 100))
            UIColor.blue.setFill(); ctx.fill(CGRect(x: 100, y: 0, width: 100, height: 100))
        }
    }

    private func couleurAuCentre(_ data: Data) throws -> (r: CGFloat, b: CGFloat, taille: CGSize) {
        let img = try XCTUnwrap(UIImage(data: data))
        let cg = try XCTUnwrap(img.cgImage)
        let pixel = UnsafeMutablePointer<UInt8>.allocate(capacity: 4)
        defer { pixel.deallocate() }
        let ctx = try XCTUnwrap(CGContext(data: pixel, width: 1, height: 1, bitsPerComponent: 8, bytesPerRow: 4,
                                          space: CGColorSpaceCreateDeviceRGB(),
                                          bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue))
        ctx.draw(cg, in: CGRect(x: -CGFloat(cg.width) / 2, y: -CGFloat(cg.height) / 2,
                                width: CGFloat(cg.width), height: CGFloat(cg.height)))
        return (CGFloat(pixel[0]) / 255, CGFloat(pixel[2]) / 255, CGSize(width: cg.width, height: cg.height))
    }

    func testCroppingKeepsTheChosenPart() throws {
        let data = try XCTUnwrap(RetoucheImageView.rendre(image(), cadre: CGRect(x: 0, y: 0, width: 0.5, height: 1),
                                                            miroirH: false, miroirV: false))
        let c = try couleurAuCentre(data)
        XCTAssertEqual(c.taille, CGSize(width: 100, height: 100))
        XCTAssertGreaterThan(c.r, 0.8, "la moitié gauche est rouge")
    }

    func testTheMirrorIsAppliedBeforeCropping() throws {
        // Miroir horizontal : le bleu passe à gauche ; on garde la moitié gauche.
        let data = try XCTUnwrap(RetoucheImageView.rendre(image(), cadre: CGRect(x: 0, y: 0, width: 0.5, height: 1),
                                                            miroirH: true, miroirV: false))
        XCTAssertGreaterThan(try couleurAuCentre(data).b, 0.8)
    }

    func testAHandleNeverShrinksTheFrameToNothing() {
        let tire = RetoucheImageView.Poignee.droite.tirer(CGRect(x: 0, y: 0, width: 1, height: 1), de: CGSize(width: -2, height: 0))
        XCTAssertGreaterThanOrEqual(tire.width, 0.08 - 1e-9)
    }
}
