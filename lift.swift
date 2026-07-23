import Foundation
import Vision
import CoreImage

let args = CommandLine.arguments
guard args.count == 3 else { print("usage: lift <in> <out.jpg>"); exit(1) }
guard let ciImage = CIImage(contentsOf: URL(fileURLWithPath: args[1])) else { print("load failed"); exit(1) }
let handler = VNImageRequestHandler(ciImage: ciImage)
let request = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([request])
guard let result = request.results?.first else { print("no subject found"); exit(2) }
let maskPB = try result.generateScaledMaskForImage(forInstances: result.allInstances, from: handler)
var maskCI = CIImage(cvPixelBuffer: maskPB)
// soften the cut edge slightly so the composite doesn't look razor-clipped
maskCI = maskCI.applyingFilter("CIGaussianBlur", parameters: ["inputRadius": 1.2])
  .cropped(to: ciImage.extent)
let white = CIImage(color: CIColor.white).cropped(to: ciImage.extent)
let blend = CIFilter(name: "CIBlendWithMask", parameters: [
  kCIInputImageKey: ciImage,
  kCIInputBackgroundImageKey: white,
  kCIInputMaskImageKey: maskCI])!
guard let out = blend.outputImage else { print("blend failed"); exit(1) }
let ctx = CIContext()
let cs = CGColorSpace(name: CGColorSpace.sRGB)!
try ctx.writeJPEGRepresentation(of: out, to: URL(fileURLWithPath: args[2]), colorSpace: cs,
  options: [kCGImageDestinationLossyCompressionQuality as CIImageRepresentationOption: 0.95])
print("ok")
