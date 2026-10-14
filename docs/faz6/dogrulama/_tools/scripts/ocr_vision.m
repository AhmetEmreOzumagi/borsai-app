#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <ImageIO/ImageIO.h>

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        if (argc != 2) {
            fprintf(stderr, "usage: ocr_vision IMAGE\n");
            return 2;
        }
        NSString *path = [NSString stringWithUTF8String:argv[1]];
        NSURL *url = [NSURL fileURLWithPath:path];
        CGImageSourceRef source = CGImageSourceCreateWithURL((__bridge CFURLRef)url, NULL);
        if (!source) return 3;
        CGImageRef image = CGImageSourceCreateImageAtIndex(source, 0, NULL);
        CFRelease(source);
        if (!image) return 4;

        VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] init];
        request.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
        request.usesLanguageCorrection = NO; request.recognitionLanguages = @[@"tr-TR", @"en-US"];
        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:image options:@{}];
        NSError *error = nil;
        BOOL ok = [handler performRequests:@[request] error:&error];
        CGImageRelease(image);
        if (!ok) {
            fprintf(stderr, "%s\n", error.localizedDescription.UTF8String);
            return 5;
        }
        NSArray<VNRecognizedTextObservation *> *observations = request.results;
        observations = [observations sortedArrayUsingComparator:^NSComparisonResult(VNRecognizedTextObservation *a, VNRecognizedTextObservation *b) {
            CGFloat ay = CGRectGetMaxY(a.boundingBox);
            CGFloat by = CGRectGetMaxY(b.boundingBox);
            if (fabs(ay - by) > 0.01) return ay > by ? NSOrderedAscending : NSOrderedDescending;
            CGFloat ax = CGRectGetMinX(a.boundingBox);
            CGFloat bx = CGRectGetMinX(b.boundingBox);
            return ax < bx ? NSOrderedAscending : (ax > bx ? NSOrderedDescending : NSOrderedSame);
        }];
        for (VNRecognizedTextObservation *observation in observations) {
            VNRecognizedText *candidate = [[observation topCandidates:1] firstObject];
            if (candidate) printf("%s\n", candidate.string.UTF8String);
        }
    }
    return 0;
}
