import Foundation
import PDFKit
let args = CommandLine.arguments
guard args.count >= 2, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else { print("ERR: cannot open"); exit(2) }
var out = ""
for i in 0..<doc.pageCount { if let p = doc.page(at: i), let s = p.string { out += "\n=== PAGE \(i+1) ===\n" + s } }
print(out)
