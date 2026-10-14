import Foundation
import PDFKit
import AppKit
let a = CommandLine.arguments
guard a.count >= 4, let doc = PDFDocument(url: URL(fileURLWithPath: a[1])), let n = Int(a[2]), let page = doc.page(at: n - 1) else { print("usage: pdfpage file.pdf pageNo out.png [scale]"); exit(2) }
let scale: CGFloat = a.count >= 5 ? CGFloat(Double(a[4]) ?? 2.0) : 2.0
let b = page.bounds(for: .mediaBox)
let img = page.thumbnail(of: CGSize(width: b.width * scale, height: b.height * scale), for: .mediaBox)
guard let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff), let png = rep.representation(using: .png, properties: [:]) else { exit(3) }
try! png.write(to: URL(fileURLWithPath: a[3]))
print("ok \(doc.pageCount) pages")
