#import <Foundation/Foundation.h>
#import <dlfcn.h>
#include <unistd.h>

@interface NSObject (BatteryLimitReading)
- (id)initWithClientName:(NSString *)name;
- (BOOL)isMCLSupported;
- (unsigned char)getMCLLimitWithError:(NSError **)error;
- (unsigned long long)isMCLCurrentlyEnabled:(NSError **)error;
@end

// Read-only native client: no charging setters, daemon, or SMC access.
int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 1) return 64;
        alarm(8);
        NSString *status = @"unsupported";
        id limit = NSNull.null, enabled = NSNull.null;
        if (dlopen("/System/Library/PrivateFrameworks/PowerUI.framework/Versions/A/PowerUI", RTLD_NOW)) {
            Class cls = NSClassFromString(@"PowerUISmartChargeClient");
            if (cls && [cls instancesRespondToSelector:@selector(initWithClientName:)]) {
                id client = [[cls alloc] initWithClientName:@"dashboard-battery-read"];
                if ([client respondsToSelector:@selector(isMCLSupported)] && [client isMCLSupported] &&
                    [client respondsToSelector:@selector(getMCLLimitWithError:)] &&
                    [client respondsToSelector:@selector(isMCLCurrentlyEnabled:)]) {
                    NSError *first = nil, *second = nil;
                    unsigned char value = [client getMCLLimitWithError:&first];
                    unsigned long long on = [client isMCLCurrentlyEnabled:&second];
                    status = @"unavailable";
                    if (!first && !second && value <= 100) {
                        status = @"ok"; limit = @(value); enabled = on ? @YES : @NO;
                    }
                }
            }
        }
        NSData *body = [NSJSONSerialization dataWithJSONObject:@{@"status":status, @"limit_percent":limit, @"limit_enabled":enabled} options:0 error:nil];
        puts([[NSString alloc] initWithData:body encoding:NSUTF8StringEncoding].UTF8String);
        return 0;
    }
}
