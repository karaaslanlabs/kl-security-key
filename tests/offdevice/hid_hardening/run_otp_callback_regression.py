#!/usr/bin/env python3
"""Compile and exercise exact OTP callback/status function bodies from the actual source.

Host-only native run; no USB hardware/keys/firmware modification. This is a
focused source-extraction test, NOT a full OTP/USB integration test.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

PREAMBLE = r"""
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
typedef int hid_report_type_t;
typedef struct { uint8_t *rdata; uint16_t rlen; uint16_t ne; } apdu_stub_t;
static apdu_stub_t apdu;
#define res_APDU (apdu.rdata)
#define res_APDU_size (apdu.rlen)
#define SW_OK() 0x9000
#define MIN(a,b) ((a)<(b)?(a):(b))
#define DEBUG_DATA(...) ((void)0)
#define ITF_HID_KB 1
#define PICO_FIDO_VERSION_MAJOR 8
#define PICO_FIDO_VERSION_MINOR 2
#define CONFIG1_VALID 1
#define CONFIG1_TOUCH 2
#define CONFIG2_VALID 4
#define CONFIG2_TOUCH 8
#define CHAL_RESP 32
#define CHAL_BTN_TRIG 64
#define PICOKEYS_OK 0
#define OTP_SLOT_PLAIN_MAX 128
#define EF_OTP_SLOT1 1
#define EF_OTP_SLOT2 2
typedef struct { uint8_t tkt_flags; uint8_t cfg_flags; } otp_config_t;
static bool scanned=true;
static uint8_t config_seq=0x11;
static uint8_t status_byte=0x22;
static unsigned char otp_frame_tx[256];
static uint8_t otp_curr_seq=0,otp_exp_seq=0;
static uint16_t pending_bytes=0;
static void scan_all(void){scanned=true;}
static bool otp_slot_has_data(int x){(void)x;return false;}
static int otp_slot_load(int x,uint8_t *p,uint16_t *len){(void)x;(void)p;(void)len;return -1;}
static void mbedtls_platform_zeroize(void *p,size_t n){memset(p,0,n);}
static uint16_t *get_send_buffer_size(uint8_t itf) { return itf==ITF_HID_KB? &pending_bytes : NULL; }
"""

TESTS = r"""
struct report_guard { uint8_t left[16], report[8], right[16]; };
static int errors=0;
static void chk(bool ok,const char *msg) {
    if(!ok){ fprintf(stderr,"OTP_REGRESSION_FAIL %s\n",msg);errors++; }
}
int main(void) {
    unsigned char original[256];
    memset(original,0x33,sizeof original);
    struct report_guard g;
    memset(&g,0xa5,sizeof g);
    apdu.rdata=original;apdu.rlen=29;apdu.ne=66;
    pending_bytes=0;otp_curr_seq=0;otp_exp_seq=0;
    uint16_t n=otp_hid_get_report_cb(ITF_HID_KB,0,0,g.report,sizeof g.report);
    chk(n==8,"response_length");
    chk(apdu.rdata==original,"apdu_rdata_restored_after_keyboard_report");
    chk(apdu.rlen==29,"apdu_rlen_restored_after_keyboard_report");
    chk(apdu.ne==66,"apdu_ne_unchanged");
    chk(g.report[0]==0,"first_report_byte_zero_not_stale");
    chk(g.report[1]==8 && g.report[2]==2 && g.report[3]==0 &&
        g.report[4]==0x11 && g.report[5]==0 && g.report[6]==0 &&
        g.report[7]==0x22,"status_payload");
    for(int i=0;i<16;i++){
        chk(g.left[i]==0xa5,"canary_left_untouched");
        chk(g.right[i]==0xa5,"canary_right_untouched");
    }
    memset(&g,0xa5,sizeof g);
    pending_bytes=7;otp_curr_seq=0;otp_exp_seq=0;
    for(unsigned i=0;i<sizeof otp_frame_tx;i++)otp_frame_tx[i]=(uint8_t)i;
    n=otp_hid_get_report_cb(ITF_HID_KB,0,0,g.report,8);
    chk(n==8 && pending_bytes==0,"keyboard_pending_chunk_size");
    chk(g.report[0]==0 && g.report[1]==1 && g.report[6]==6 &&
        g.report[7]==0x40,"keyboard_pending_frame");
    chk(apdu.rdata==original,"apdu_rdata_after_pending");
    memset(&g,0xa5,sizeof g);
    pending_bytes=0;otp_curr_seq=1;otp_exp_seq=1;
    n=otp_hid_get_report_cb(ITF_HID_KB,0,0,g.report,8);
    chk(n==8 && g.report[7]==0x40 && otp_curr_seq==0 && otp_exp_seq==0,
        "keyboard_terminal_frame");
    chk(g.report[0]==0,"keyboard_terminal_zero_prefix");
    chk(apdu.rdata==original,"apdu_rdata_after_terminal");
    uint8_t extended[16];
    memset(extended,0xa5,sizeof extended);
    pending_bytes=0;otp_curr_seq=0;otp_exp_seq=0;
    n=otp_hid_get_report_cb(ITF_HID_KB,0,0,extended,sizeof extended);
    chk(n==8,"large_host_report_is_clamped_to_eight");
    chk(extended[0]==0,"large_host_report_first_byte_clean");
    for(int i=8;i<16;i++)chk(extended[i]==0xa5,"large_host_report_tail_not_sent");
    chk(apdu.rdata==original && apdu.rlen==29,"apdu_state_after_large_report");
    chk(otp_hid_get_report_cb(22,0,0,g.report,8)==0,"invalid_interface");
    chk(otp_hid_get_report_cb(ITF_HID_KB,0,0,g.report,7)==0,"short_report");
    chk(otp_hid_get_report_cb(ITF_HID_KB,0,0,NULL,8)==0,"null_report");
    if(!errors)puts("OTP_REAL_SOURCE_CALLBACK_PASS pointer_lifetime_first_byte_canaries_framing");
    return errors ? 1 : 0;
}
"""

def extract_function(source: str, signature: str) -> str:
    found = re.search(signature + r"\s*\{", source, re.MULTILINE | re.DOTALL)
    if not found:
        raise ValueError("Expected source function not found: " + signature)
    beginning = found.start()
    depth = 1
    pos = found.end()
    while pos < len(source) and depth:
        ch = source[pos]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        pos += 1
    if depth:
        raise ValueError("Unbalanced function braces")
    return source[beginning:pos]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--otp-source",required=True,type=Path)
    args=p.parse_args()
    src=args.otp_source.read_text()
    status=extract_function(src, r"static uint16_t otp_status\(bool is_otp\)")
    get=extract_function(src, r"static uint16_t otp_hid_get_report_cb\(uint8_t itf,.*?uint16_t reqlen\)")
    code=PREAMBLE+"\n"+status+"\n"+get+"\n"+TESTS
    with tempfile.TemporaryDirectory(prefix="kl-otp-native-") as wd:
        raw=Path(wd)/"extracted_otp.c"
        exe=Path(wd)/"otp_regression"
        raw.write_text(code)
        compile_cmd=["gcc","-std=gnu11","-O1","-g","-Wall","-Wextra",
                     "-Wno-unused-function","-fsanitize=address,undefined",
                     "-fno-omit-frame-pointer","-no-pie",str(raw),"-o",str(exe)]
        built=subprocess.run(compile_cmd,capture_output=True,text=True)
        if built.returncode:
            print("OTP_SOURCE_COMPILE_FAIL",built.stderr[-4000:])
            return 2
        env={**os.environ,"ASAN_OPTIONS":"detect_leaks=0"}
        tested=subprocess.run([str(exe)],capture_output=True,text=True,env=env)
        print("OTP_SOURCE_COMPILE_PASS")
        print((tested.stdout+tested.stderr)[-4500:])
        return tested.returncode

if __name__=="__main__":
    raise SystemExit(main())
