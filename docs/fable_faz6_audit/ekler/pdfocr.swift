import Foundation
import PDFKit
import Vision
import AppKit
let args = CommandLine.arguments
guard args.count >= 2, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else { print("ERR: cannot open"); exit(2) }
let scale: CGFloat = args.count >= 3 ? CGFloat(Double(args[2]) ?? 3.0) : 3.0
var out = ""
for i in 0..<doc.pageCount {
    guard let page = doc.page(at: i) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let size = CGSize(width: bounds.width * scale, height: bounds.height * scale)
    let img = page.thumbnail(of: size, for: .mediaBox)
    guard let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["tr-TR", "en-US"]
    req.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([req])
    out += "\n=== PAGE \(i+1) ===\n"
    let obs = (req.results ?? []).sorted { a, b in
        let ay = a.boundingBox.midY, by = b.boundingBox.midY
        if abs(ay - by) > 0.006 { return ay > by }
        return a.boundingBox.minX < b.boundingBox.minX
    }
    for o in obs { if let c = o.topCandidates(1).first { out += c.string + "\n" } }
}
print(out)
