#pragma once
#include <stdint.h>
#include <stdbool.h>
typedef enum {HID_REPORT_TYPE_INVALID=0,HID_REPORT_TYPE_INPUT=1,HID_REPORT_TYPE_OUTPUT=2,HID_REPORT_TYPE_FEATURE=3} hid_report_type_t;
#define BOARD_TUD_RHPORT 0
#define HID_ASCII_TO_KEYCODE {0,0}
#define KEYBOARD_MODIFIER_LEFTSHIFT 2
bool tud_init(uint8_t);
bool tud_hid_ready(void);
bool tud_hid_n_report(uint8_t,uint8_t,const void *,uint16_t);
bool tud_hid_n_keyboard_report(uint8_t,uint8_t,uint8_t,const uint8_t *);
bool tud_suspended(void);
bool tud_remote_wakeup(void);
