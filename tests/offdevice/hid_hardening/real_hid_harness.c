/* Off-device test only. Includes the actual embedded HID source and real
 * ctap_hid.h, usb.h, apdu.h, byte_array.h. Never ENABLE_EMULATION. No application,
 * storage, crypto, attestation, device or provisioning code is linked. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>
#include <stdarg.h>

static unsigned alloc_calls, fail_mask, outstanding_allocs;
static void *tracked_calloc(size_t n,size_t s) {
    unsigned call=++alloc_calls;
    if(call <= 32 && (fail_mask & (1u << (call-1)))) return NULL;
    void *p=calloc(n,s);if(p)outstanding_allocs++;return p;
}
static void __attribute__((unused)) tracked_free(void *p) {if(p){assert(outstanding_allocs>0);outstanding_allocs--;}free(p);}
static int quiet_printf(const char *fmt,...) {(void)fmt;return 0;}
#define calloc tracked_calloc
#define free tracked_free
#define printf quiet_printf
#include HID_SOURCE
#undef printf
#undef calloc
#undef free

_Static_assert(USB_BUFFER_SIZE==2048,"Must test embedded USB_BUFFER_SIZE");
_Static_assert(CTAP_MAX_PACKET_SIZE==7609,"Unexpected CTAP max");
_Static_assert(sizeof(CTAPHID_FRAME)==64,"Unexpected CTAP frame");
#ifdef ENABLE_EMULATION
#error ENABLE_EMULATION would test alternate transport/buffer configuration
#endif

uint8_t ITF_HID_CTAP=0,ITF_HID_KB=1,ITF_HID=0,ITF_KEYBOARD=1,ITF_HID_TOTAL=2,ITF_TOTAL=2;
struct apdu apdu;
struct serial_stub pico_serial;
bool cancel_button;
volatile uint16_t finished_data_size;
const uint8_t fido_aid[]={1,0xF1},u2f_aid[]={1,0xF2},oath_aid[]={1,0xF3};
static uint32_t clock_ms=1000;
static int stub_card_status=1;
static bool pending;
static uint8_t pending_report[64];
static uint8_t pending_itf;
static size_t captured_n;
static uint8_t captured[140][64];
static unsigned dispatch_count;
static uint8_t dispatch_command,dispatch_iface;
static uint8_t dispatch_data[7609];
static size_t dispatch_len;
static unsigned select_count,card_start_count,event_count;
static unsigned tinyusb_init_count;
uint32_t board_millis(void) {return clock_ms;}
void sleep_ms(unsigned n) {clock_ms+=n;}
bool tud_init(uint8_t itf) {(void)itf;++tinyusb_init_count;return true;}
bool tud_hid_ready(void) {return true;}
bool tud_hid_n_keyboard_report(uint8_t a,uint8_t b,uint8_t c,const uint8_t *d) {(void)a;(void)b;(void)c;(void)d;return true;}
bool tud_suspended(void) {return false;}
bool tud_remote_wakeup(void) {return true;}
bool tud_hid_n_report(uint8_t itf,uint8_t report_id,const void *p,uint16_t len) {
    assert(itf<ITF_HID_TOTAL);assert(report_id==0);assert(p);assert(len==64);
    assert(!pending);assert(captured_n<140);
    memcpy(pending_report,p,64);pending_itf=itf;pending=true;
    memcpy(captured[captured_n++],pending_report,64);
    return true;
}
void usb_set_timeout_counter(uint8_t i,uint32_t v) {(void)i;(void)v;}
void init_fido(void) {}
bool is_busy(void) {return false;}
void timeout_stop(void) {}
bool is_req_button_pending(void) {return false;}
void card_exit(void) {}
int select_app(const_byte_array_t aid) {assert(aid.len==1);++select_count;return 0;}
void *apdu_thread(void *p) {return p;}
void *cbor_thread(void *p) {return p;}
void card_start(uint8_t i,void *(*f)(void *)) {(void)i;(void)f;++card_start_count;}
void usb_send_event(uint32_t flag) {assert(flag==EV_CMD_AVAILABLE);++event_count;}
int card_status(uint8_t i) {(void)i;return stub_card_status;}
static void record_dispatch(uint8_t command,uint8_t itf,const uint8_t *d,size_t n) {
    assert(n<=7609);assert(d || n==0);dispatch_count++;dispatch_command=command;
    dispatch_iface=itf;dispatch_len=n;if(n)memcpy(dispatch_data,d,n);
}
static bool simulate_apdu_pending;
bool apdu_is_response_pending(void) {return simulate_apdu_pending;}
uint16_t apdu_process(uint8_t itf,const_byte_array_t b) {record_dispatch(CTAPHID_MSG,itf,b.data,b.len);return 1;}
int cbor_process(uint8_t cmd,const uint8_t *p,size_t len) {record_dispatch(cmd,ITF_HID_CTAP,p,len);return 2;}

static void complete(void) {
    if(!pending)return;
    uint8_t immutable[64];memcpy(immutable,pending_report,64);
    uint8_t itf=pending_itf;pending=false;
    tud_hid_report_complete_cb(itf,immutable,64);
}
static void drain(void) {
    for(unsigned i=0;i<140;i++) {
        if(pending)complete();
        clock_ms++;hid_task();
        if(!pending && hid_tx && hid_tx[ITF_HID_CTAP].r_ptr==hid_tx[ITF_HID_CTAP].w_ptr)return;
    }
    assert(!"TX failed to drain within 140 reports");
}
static void clear_capture(void) {assert(!pending);captured_n=0;dispatch_count=select_count=card_start_count=event_count=0;}
static void patterned(uint8_t *p,size_t n) {for(size_t i=0;i<n;i++)p[i]=(uint8_t)((i*37u+11u)&255);}
static CTAPHID_FRAME first(uint32_t cid,uint8_t cmd,size_t n,const uint8_t *p) {
    CTAPHID_FRAME f={0};f.cid=cid;f.init.cmd=cmd;f.init.bcnth=n>>8;f.init.bcntl=n;
    size_t take=n<57?n:57;if(take)memcpy(f.init.data,p,take);return f;
}
static void report(const CTAPHID_FRAME *f) {tud_hid_set_report_cb(ITF_HID_CTAP,0,HID_REPORT_TYPE_OUTPUT,(const uint8_t *)f,64);}
static void send_message(uint32_t cid,uint8_t cmd,size_t n,const uint8_t *p) {
    CTAPHID_FRAME f=first(cid,cmd,n,p);report(&f);
    size_t used=n<57?n:57;uint8_t seq=0;
    while(used<n) {f=(CTAPHID_FRAME){0};f.cid=cid;f.cont.seq=seq++;
        size_t take=n-used<59?n-used:59;memcpy(f.cont.data,p+used,take);report(&f);used+=take;}
}
static bool verify_padding;
static void verify_echo(uint32_t cid,uint8_t cmd,size_t n,const uint8_t *expected) {
    size_t expected_reports=1+(n>57?(n-57+58)/59:0);
    assert(captured_n==expected_reports);
    CTAPHID_FRAME *f=(CTAPHID_FRAME *)captured[0];
    assert(f->cid==cid && f->init.cmd==cmd && (size_t)MSG_LEN(f)==n);
    size_t used=n<57?n:57;assert(!used || !memcmp(f->init.data,expected,used));
    for(size_t i=1;i<captured_n;i++) {f=(CTAPHID_FRAME *)captured[i];assert(f->cid==cid && f->cont.seq==i-1);
        size_t take=n-used<59?n-used:59;assert(!memcmp(f->cont.data,expected+used,take));used+=take;}
    if(verify_padding) {
        size_t last_payload=n<=57?n:(n-57)%59;
        if(n>57 && last_payload==0)last_payload=59;
        size_t end=(captured_n==1?7:5)+last_payload;
        for(size_t i=end;i<64;i++)assert(captured[captured_n-1][i]==0);
    }
    assert(used==n);assert(!pending);assert(hid_tx[0].w_ptr==0 && hid_tx[0].r_ptr==0);
}
static void check_echo(uint8_t cmd,size_t n) {
    uint8_t data[7609];patterned(data,n);clear_capture();send_message(0x1234ABCD,cmd,n,data);drain();
    verify_echo(0x1234ABCD,cmd,n,data);
    assert(hid_rx[0].r_ptr==0 && hid_rx[0].w_ptr==0);assert(msg_packet.len==0);
}
static void verify_error(uint32_t cid,uint8_t error) {
    drain();assert(captured_n==1);CTAPHID_FRAME *f=(CTAPHID_FRAME *)captured[0];
    assert(f->cid==cid && f->init.cmd==CTAPHID_ERROR && MSG_LEN(f)==1 && f->init.data[0]==error);
}
static void reset_protocol(void) {msg_packet.len=msg_packet.current_len=0;last_packet_time=0;last_cmd_time=0;last_seq=0;lock=0;thread_type=0;apdu.sw=0;is_nk=false;}
static void benign_callbacks(void) {
    CTAPHID_FRAME f=first(0x1234ABCD,CTAPHID_PING,0,NULL);uint8_t out[64]={0};
    tud_hid_get_report_cb(255,0,HID_REPORT_TYPE_INPUT,out,sizeof(out));
    tud_hid_set_report_cb(255,0,HID_REPORT_TYPE_OUTPUT,(uint8_t *)&f,64);
    tud_hid_set_report_cb(0,0,HID_REPORT_TYPE_OUTPUT,(uint8_t *)&f,64);
    tud_hid_report_complete_cb(0,(uint8_t *)&f,64);
    tud_hid_report_complete_cb(255,(uint8_t *)&f,64);
    driver_write_hid(255,CONST_BYTE_ARRAY((uint8_t *)&f,64));
    if(ITF_HID_CTAP!=255)driver_write_hid(0,CONST_BYTE_ARRAY((uint8_t *)&f,64));
    (void)get_send_buffer_size(0);(void)get_send_buffer_size(255);
    (void)driver_init_hid();(void)driver_process_usb_packet_hid(64);
    (void)ctap_error(CTAP1_ERR_OTHER);driver_exec_finished_hid(1);
    driver_exec_finished_cont_hid(0,1,7);driver_exec_finished_cont_hid(255,1,7);
    hid_task();assert(!pending);
}
static void initialized_adversarial(void) {
    CTAPHID_FRAME f=first(0x1234ABCD,CTAPHID_PING,0,NULL);uint8_t out[64]={0};clear_capture();
    assert(get_send_buffer_size(255)==NULL);
    assert(driver_write_hid(255,CONST_BYTE_ARRAY((uint8_t *)&f,64))==0);
    assert(driver_write_hid(0,CONST_BYTE_ARRAY(NULL,64))==0);
    assert(driver_write_hid(0,CONST_BYTE_ARRAY((uint8_t *)&f,65536))==0);
    tud_hid_set_report_cb(0,0,HID_REPORT_TYPE_OUTPUT,NULL,64);
    tud_hid_set_report_cb(0,0,HID_REPORT_TYPE_OUTPUT,(uint8_t *)&f,0);
    tud_hid_set_report_cb(0,0,HID_REPORT_TYPE_OUTPUT,(uint8_t *)&f,63);
    tud_hid_set_report_cb(255,0,HID_REPORT_TYPE_OUTPUT,(uint8_t *)&f,64);
    tud_hid_get_report_cb(0,0,HID_REPORT_TYPE_INPUT,NULL,64);
    tud_hid_get_report_cb(255,0,HID_REPORT_TYPE_INPUT,out,64);
    tud_hid_report_complete_cb(0,NULL,64);tud_hid_report_complete_cb(255,(uint8_t *)&f,64);
    tud_hid_report_complete_cb(0,(uint8_t *)&f,63);
    assert(captured_n==0 && !pending);
    const uint16_t corrupt[][2]={{0,2048},{0,2049},{0,65535},{2048,2048},{2049,2049},{65535,65535},{128,64}};
    for(size_t i=0;i<sizeof(corrupt)/sizeof(*corrupt);i++) {
        hid_rx[0].r_ptr=corrupt[i][0];hid_rx[0].w_ptr=corrupt[i][1];report(&f);drain();
        assert(hid_rx[0].r_ptr<=2048 && hid_rx[0].w_ptr<=2048);reset_protocol();clear_capture();check_echo(CTAPHID_PING,64);
    }
    puts("PASS: callbacks, invalid iface=255, NULL/short reports, RX pointer corruption and recovery");
}
static void protocol_errors(void) {
    uint8_t data[7609];patterned(data,sizeof(data));
    for(size_t n=7610;n<=65535;n=n==7610?8192:65535) {clear_capture();CTAPHID_FRAME f=first(0x1234ABCD,CTAPHID_PING,n,data);report(&f);verify_error(f.cid,CTAP1_ERR_INVALID_LEN);reset_protocol();if(n==65535)break;check_echo(CTAPHID_PING,7609);}
    clear_capture();CTAPHID_FRAME f=first(0,CTAPHID_PING,0,NULL);report(&f);verify_error(0,CTAP1_ERR_INVALID_CHANNEL);reset_protocol();
    clear_capture();f=first(CID_BROADCAST,CTAPHID_PING,0,NULL);report(&f);verify_error(CID_BROADCAST,CTAP1_ERR_INVALID_CHANNEL);reset_protocol();
    clear_capture();f=first(0x1234ABCD,CTAPHID_PING,116,data);report(&f);f=(CTAPHID_FRAME){0};f.cid=0x1234ABCD;f.cont.seq=1;report(&f);verify_error(f.cid,CTAP1_ERR_INVALID_SEQ);reset_protocol();check_echo(CTAPHID_PING,7609);
    clear_capture();f=first(0x1234ABCD,CTAPHID_PING,116,data);report(&f);f=(CTAPHID_FRAME){0};f.cid=0x11223344;f.cont.seq=0;report(&f);verify_error(f.cid,CTAP1_ERR_CHANNEL_BUSY);reset_protocol();check_echo(CTAPHID_PING,2048);
    clear_capture();f=first(0x1234ABCD,CTAPHID_PING,116,data);report(&f);clock_ms+=501;hid_task();verify_error(f.cid,CTAP1_ERR_MSG_TIMEOUT);reset_protocol();check_echo(CTAPHID_PING,64);
    puts("PASS: invalid lengths 7610/8192/65535, invalid/broadcast CID, sequence/CID/timeout errors and recovery");
}
static void dispatches(void) {
    const size_t lengths[]={0,1,57,58,2048,7609};uint8_t data[7609];patterned(data,sizeof(data));
    const uint8_t commands[]={CTAPHID_CBOR,CTAPHID_MSG};
    for(size_t c=0;c<2;c++)for(size_t l=0;l<6;l++) {
        reset_protocol();clear_capture();size_t n=lengths[l];send_message(0x1234ABCD,commands[c],n,data);drain();
        assert(dispatch_count==1 && dispatch_command==commands[c] && dispatch_iface==0 && dispatch_len==n);
        assert(n==0 || !memcmp(dispatch_data,data,n));assert(card_start_count==1 && event_count==1 && select_count==1);
        assert(msg_packet.len==0 && msg_packet.current_len==0 && hid_rx[0].r_ptr==0 && hid_rx[0].w_ptr==0);
    }
    reset_protocol();puts("PASS: exact CBOR/MSG stub dispatch at 0,1,57,58,2048,7609; no real app workers linked");
}
static void direct_completion(void) {
    uint8_t data[7609];patterned(data,sizeof(data));reset_protocol();clear_capture();
    CTAPHID_FRAME req=first(0x1234ABCD,CTAPHID_PING,7609,data);report(&req);
    /* Direct worker completion starts at absolute APDU data offset seven. */
    reset_protocol();last_cmd=CTAPHID_PING;memcpy(apdu.rdata,data,7609);driver_exec_finished_cont_hid(0,7609,7);drain();verify_echo(req.cid,CTAPHID_PING,7609,data);
    const uint16_t offsets[]={7,8,13,14,64,263};
    const uint16_t sizes[]={1,57,58,200,2048};
    for(size_t o=0;o<6;o++)for(size_t z=0;z<5;z++) {
        reset_protocol();clear_capture();(void)driver_init_hid();last_cmd=CTAPHID_MSG;
        memset(hid_tx[0].buffer,0xA5,sizeof(hid_tx[0].buffer));
        memcpy(hid_tx[0].buffer+offsets[o],data,sizes[z]);
        driver_exec_finished_cont_hid(0,sizes[z],offsets[o]);drain();verify_echo(req.cid,CTAPHID_MSG,sizes[z],data);
    }
    const uint16_t invalid[][2]={{7610,7},{65535,7},{1,0},{1,6},{7609,8},{1,65535}};
    for(size_t i=0;i<sizeof(invalid)/sizeof(*invalid);i++) {reset_protocol();clear_capture();(void)driver_init_hid();driver_exec_finished_cont_hid(0,invalid[i][0],invalid[i][1]);verify_error(req.cid,CTAP1_ERR_INVALID_LEN);}
    reset_protocol();clear_capture();(void)driver_init_hid();driver_exec_finished_cont_hid(255,1,7);drain();assert(captured_n==0);
    is_nk=true;driver_exec_finished_hid(1);verify_error(req.cid,CTAP1_ERR_INVALID_LEN);is_nk=false;
    puts("PASS: direct max TX, valid offsets 7/8/13/14/64/263, zero padding, invalid size/offset/interface completion and NK underflow guard");
}
static void runtime_interfaces(void) {
    const uint8_t invalid_counts[]={0,3,255};
    for(size_t i=0;i<3;i++) {
        ITF_HID_TOTAL=invalid_counts[i];benign_callbacks();assert(get_send_buffer_size(0)==NULL);
        ITF_HID_TOTAL=2;check_echo(CTAPHID_PING,64);
    }
    ITF_HID_CTAP=255;benign_callbacks();assert(get_send_buffer_size(255)==NULL);
    ITF_HID_CTAP=0;check_echo(CTAPHID_PING,7609);
    puts("PASS: runtime interface count 0/3/255 and disabled CTAP iface255 fail closed and recover");
}

static int pending_apdu_leak_regression(void) {
    int failed=0;
    const uint8_t expected_ver[4]={PICOKEYS_SDK_VERSION_MAJOR,PICOKEYS_SDK_VERSION_MINOR,0,0};
    reset_protocol();clear_capture();assert(driver_init_hid()==0);
    memset(hid_tx[0].buffer+7,0xa5,512);
    simulate_apdu_pending=true;
    CTAPHID_FRAME f=first(0x1234ABCD,CTAPHID_VERSION,0,NULL);
    report(&f);drain();
    assert(captured_n==1);
    CTAPHID_FRAME *out=(CTAPHID_FRAME *)captured[0];
    if(out->init.cmd!=CTAPHID_VERSION || MSG_LEN(out)!=4 ||
       memcmp(out->init.data,expected_ver,4)!=0) {
       printf("FAIL: pending APDU VERSION stale bytes %02x %02x %02x %02x\n",
           out->init.data[0],out->init.data[1],out->init.data[2],out->init.data[3]);
       failed++;
    }
    reset_protocol();clear_capture();assert(driver_init_hid()==0);
    memset(hid_tx[0].buffer+7,0xa5,512);
    uint8_t nonce[8]={1,2,3,4,5,6,7,8};
    f=first(CID_BROADCAST,CTAPHID_INIT,sizeof nonce,nonce);
    report(&f);drain();
    assert(captured_n==1);
    out=(CTAPHID_FRAME *)captured[0];
    if(out->init.cmd!=CTAPHID_INIT || MSG_LEN(out)!=17 ||
       memcmp(out->init.data,nonce,8)!=0 || out->init.data[15]!=0) {
       printf("FAIL: pending APDU INIT versionBuild %02x\n",out->init.data[15]);
       failed++;
    }
    simulate_apdu_pending=false;
    printf("PENDING_APDU_INIT_VERSION_REGRESSION %s\n",failed?"FAIL":"PASS");
    return failed?1:0;
}

int main(int argc,char **argv) {
    setvbuf(stdout,NULL,_IONBF,0);const char *mode=argc>1?argv[1]:"all";
    if(!strcmp(mode,"fido-only")) {
        ITF_HID_TOTAL=ITF_TOTAL=1;ITF_HID_KB=ITF_KEYBOARD=ITF_INVALID;
        fail_mask=argc>2?strtoul(argv[2],NULL,0):0;hid_init();
        if(fail_mask) {benign_callbacks();assert(outstanding_allocs==0);fail_mask=0;hid_init();}
        assert(driver_init_hid()==0);assert(get_send_buffer_size(ITF_HID_KB)==NULL);verify_padding=true;
        for(size_t n=0;n<=7609;n++)check_echo(CTAPHID_PING,n);
        printf("PASS: FIDO-only one HID interface, disabled keyboard, initial alloc mask %u, all 7610 payloads, logical HID allocation %zu bytes\n",argc>2?(unsigned)strtoul(argv[2],NULL,0):0,sizeof(uint16_t)+sizeof(write_status_t)+sizeof(usb_buffer_t)+sizeof(hid_tx_buffer_t));
        return 0;
    }
    if(!strcmp(mode,"pending-apdu-leak")) {hid_init();assert(driver_init_hid()==0);return pending_apdu_leak_regression();}
    if(!strcmp(mode,"before-init")) {benign_callbacks();puts("PASS: callbacks before init fail closed");return 0;}
    if(!strcmp(mode,"oom")) {fail_mask=argc>2?strtoul(argv[2],NULL,0):1;hid_init();assert(alloc_calls==4);
#ifdef TEST_CURRENT
        assert(!send_buffer_size && !last_write_result && !hid_rx && !hid_tx && outstanding_allocs==0);
#endif
        benign_callbacks();assert(!pending);
        fail_mask=0;hid_init();assert(driver_init_hid()==0);
#ifdef TEST_CURRENT
        assert(alloc_calls==8 && outstanding_allocs==4);
#endif
        check_echo(CTAPHID_PING,7609);printf("PASS: alloc failure mask %u, all callbacks fail closed, retry max PING\n",argc>2?(unsigned)strtoul(argv[2],NULL,0):1);return 0;}
    hid_init();assert(alloc_calls==4);assert(driver_init_hid()==0);
    printf("Embedded configuration: USB_BUFFER_SIZE=%u HID_TX_BUFFER_SIZE=%zu CTAP_MAX_PACKET_SIZE=%u\n",(unsigned)USB_BUFFER_SIZE,sizeof(hid_tx[0].buffer),(unsigned)CTAP_MAX_PACKET_SIZE);
    if(!strcmp(mode,"control")) {check_echo(CTAPHID_PING,2048);check_echo(CTAPHID_PING,7609);puts("PASS: baseline real-source 2048/7609 end-to-end controls");return 0;}
    if(!strcmp(mode,"padding")) {verify_padding=true;check_echo(CTAPHID_PING,7609);check_echo(CTAPHID_PING,58);puts("PASS: long-to-short response padding");return 0;}
    if(!strcmp(mode,"offset")) {check_echo(CTAPHID_PING,0);clear_capture();driver_init_hid();last_cmd=CTAPHID_MSG;driver_exec_finished_cont_hid(0,1,0);verify_error(0x1234ABCD,CTAP1_ERR_INVALID_LEN);puts("PASS: offset zero rejected before pointer arithmetic");return 0;}
    verify_padding=true;initialized_adversarial();reset_protocol();runtime_interfaces();
    for(size_t n=0;n<=7609;n++)check_echo(CTAPHID_PING,n);
    puts("PASS: all 7610 PING lengths 0..7609, complete payload/CID/sequence/asynchronous immutable completion");
    const size_t sync_lengths[]={0,1,57,58,2048,7609};for(size_t i=0;i<6;i++)check_echo(CTAPHID_SYNC,sync_lengths[i]);
    puts("PASS: SYNC 0,1,57,58,2048,7609");protocol_errors();dispatches();direct_completion();
    puts("PASS: real embedded HID suite");return 0;
}
