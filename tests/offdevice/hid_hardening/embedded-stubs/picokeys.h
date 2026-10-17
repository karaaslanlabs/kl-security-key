#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "compat/compat.h"
#define MIN(a,b) ({ __typeof__(a) _a=(a); __typeof__(b) _b=(b); _a<_b?_a:_b; })
#define DEBUG_PAYLOAD(a,b) ((void)0)
#define PICOKEYS_OK 0
#define PICOKEYS_ERR_NO_MEMORY -1000
#define PICOKEYS_ERR_MEMORY_FATAL -1001
#define PICOKEYS_ERR_NULL_PARAM -1002
#define PICOKEYS_ERR_BLOCKED -1004
#define PICOKEYS_WRONG_LENGTH -1007
#define PICOKEYS_ERR_INVALID_DATA -1008
static inline uint8_t put_uint16_be(uint16_t n, uint8_t *b) {b[0]=n>>8;b[1]=n;return 2;}

static inline uint16_t make_uint16_be(uint8_t a,uint8_t b){return ((uint16_t)a<<8)|b;}
static inline uint16_t get_uint16_be(const uint8_t *b){return make_uint16_be(b[0],b[1]);}
