from __future__ import annotations
from enum import IntEnum


class CharacterSet(IntEnum):
    big5 = 1
    dec8 = 3
    cp850 = 4
    hp8 = 6
    koi8r = 7
    latin1 = 8
    latin2 = 9
    swe7 = 10
    ascii = 11
    ujis = 12
    sjis = 13
    hebrew = 16
    tis620 = 18
    euckr = 19
    koi8u = 22
    gb2312 = 24
    greek = 25
    cp1250 = 26
    gbk = 28
    latin5 = 30
    armscii8 = 32
    utf8 = 33
    ucs2 = 35
    cp866 = 36
    keybcs2 = 37
    macce = 38
    macroman = 39
    cp852 = 40
    latin7 = 41
    cp1251 = 51
    utf16 = 54
    utf16le = 56
    cp1256 = 57
    cp1257 = 59
    utf32 = 60
    binary = 63
    geostd8 = 92
    cp932 = 95
    eucjpms = 97
    gb18030 = 248
    utf8mb4 = 255

    @property
    def codec(self) -> str:
        if self.name == "utf8mb4":
            return "utf8"
        return self.name

    @property
    def default_collation(self) -> Collation:
        return DEFAULT_COLLATIONS[self]

    def decode(self, b: bytes | bytearray) -> str:
        return b.decode(self.codec)

    def encode(self, s: str) -> bytes:
        return s.encode(self.codec)


class Collation(IntEnum):
    big5_chinese_ci = 1
    latin2_czech_cs = 2
    dec8_swedish_ci = 3
    cp850_general_ci = 4
    latin1_german1_ci = 5
    hp8_english_ci = 6
    koi8r_general_ci = 7
    latin1_swedish_ci = 8
    latin2_general_ci = 9
    swe7_swedish_ci = 10
    ascii_general_ci = 11
    ujis_japanese_ci = 12
    sjis_japanese_ci = 13
    cp1251_bulgarian_ci = 14
    latin1_danish_ci = 15
    hebrew_general_ci = 16
    tis620_thai_ci = 18
    euckr_korean_ci = 19
    latin7_estonian_cs = 20
    latin2_hungarian_ci = 21
    koi8u_general_ci = 22
    cp1251_ukrainian_ci = 23
    gb2312_chinese_ci = 24
    greek_general_ci = 25
    cp1250_general_ci = 26
    latin2_croatian_ci = 27
    gbk_chinese_ci = 28
    cp1257_lithuanian_ci = 29
    latin5_turkish_ci = 30
    latin1_german2_ci = 31
    armscii8_general_ci = 32
    utf8_general_ci = 33
    cp1250_czech_cs = 34
    ucs2_general_ci = 35
    cp866_general_ci = 36
    keybcs2_general_ci = 37
    macce_general_ci = 38
    macroman_general_ci = 39
    cp852_general_ci = 40
    latin7_general_ci = 41
    latin7_general_cs = 42
    macce_bin = 43
    cp1250_croatian_ci = 44
    utf8mb4_general_ci = 45
    utf8mb4_bin = 46
    latin1_bin = 47
    latin1_general_ci = 48
    latin1_general_cs = 49
    cp1251_bin = 50
    cp1251_general_ci = 51
    cp1251_general_cs = 52
    macroman_bin = 53
    utf16_general_ci = 54
    utf16_bin = 55
    utf16le_general_ci = 56
    cp1256_general_ci = 57
    cp1257_bin = 58
    cp1257_general_ci = 59
    utf32_general_ci = 60
    utf32_bin = 61
    utf16le_bin = 62
    binary = 63
    armscii8_bin = 64
    ascii_bin = 65
    cp1250_bin = 66
    cp1256_bin = 67
    cp866_bin = 68
    dec8_bin = 69
    greek_bin = 70
    hebrew_bin = 71
    hp8_bin = 72
    keybcs2_bin = 73
    koi8r_bin = 74
    koi8u_bin = 75
    latin2_bin = 77
    latin5_bin = 78
    latin7_bin = 79
    cp850_bin = 80
    cp852_bin = 81
    swe7_bin = 82
    utf8_bin = 83
    big5_bin = 84
    euckr_bin = 85
    gb2312_bin = 86
    gbk_bin = 87
    sjis_bin = 88
    tis620_bin = 89
    ucs2_bin = 90
    ujis_bin = 91
    geostd8_general_ci = 92
    geostd8_bin = 93
    latin1_spanish_ci = 94
    cp932_japanese_ci = 95
    cp932_bin = 96
    eucjpms_japanese_ci = 97
    eucjpms_bin = 98
    cp1250_polish_ci = 99
    utf16_unicode_ci = 101
    utf16_icelandic_ci = 102
    utf16_latvian_ci = 103
    utf16_romanian_ci = 104
    utf16_slovenian_ci = 105
    utf16_polish_ci = 106
    utf16_estonian_ci = 107
    utf16_spanish_ci = 108
    utf16_swedish_ci = 109
    utf16_turkish_ci = 110
    utf16_czech_ci = 111
    utf16_danish_ci = 112
    utf16_lithuanian_ci = 113
    utf16_slovak_ci = 114
    utf16_spanish2_ci = 115
    utf16_roman_ci = 116
    utf16_persian_ci = 117
    utf16_esperanto_ci = 118
    utf16_hungarian_ci = 119
    utf16_sinhala_ci = 120
    utf16_german2_ci = 121
    utf16_croatian_ci = 122
    utf16_unicode_520_ci = 123
    utf16_vietnamese_ci = 124
    ucs2_unicode_ci = 128
    ucs2_icelandic_ci = 129
    ucs2_latvian_ci = 130
    ucs2_romanian_ci = 131
    ucs2_slovenian_ci = 132
    ucs2_polish_ci = 133
    ucs2_estonian_ci = 134
    ucs2_spanish_ci = 135
    ucs2_swedish_ci = 136
    ucs2_turkish_ci = 137
    ucs2_czech_ci = 138
    ucs2_danish_ci = 139
    ucs2_lithuanian_ci = 140
    ucs2_slovak_ci = 141
    ucs2_spanish2_ci = 142
    ucs2_roman_ci = 143
    ucs2_persian_ci = 144
    ucs2_esperanto_ci = 145
    ucs2_hungarian_ci = 146
    ucs2_sinhala_ci = 147
    ucs2_german2_ci = 148
    ucs2_croatian_ci = 149
    ucs2_unicode_520_ci = 150
    ucs2_vietnamese_ci = 151
    ucs2_general_mysql500_ci = 159
    utf32_unicode_ci = 160
    utf32_icelandic_ci = 161
    utf32_latvian_ci = 162
    utf32_romanian_ci = 163
    utf32_slovenian_ci = 164
    utf32_polish_ci = 165
    utf32_estonian_ci = 166
    utf32_spanish_ci = 167
    utf32_swedish_ci = 168
    utf32_turkish_ci = 169
    utf32_czech_ci = 170
    utf32_danish_ci = 171
    utf32_lithuanian_ci = 172
    utf32_slovak_ci = 173
    utf32_spanish2_ci = 174
    utf32_roman_ci = 175
    utf32_persian_ci = 176
    utf32_esperanto_ci = 177
    utf32_hungarian_ci = 178
    utf32_sinhala_ci = 179
    utf32_german2_ci = 180
    utf32_croatian_ci = 181
    utf32_unicode_520_ci = 182
    utf32_vietnamese_ci = 183
    utf8_unicode_ci = 192
    utf8_icelandic_ci = 193
    utf8_latvian_ci = 194
    utf8_romanian_ci = 195
    utf8_slovenian_ci = 196
    utf8_polish_ci = 197
    utf8_estonian_ci = 198
    utf8_spanish_ci = 199
    utf8_swedish_ci = 200
    utf8_turkish_ci = 201
    utf8_czech_ci = 202
    utf8_danish_ci = 203
    utf8_lithuanian_ci = 204
    utf8_slovak_ci = 205
    utf8_spanish2_ci = 206
    utf8_roman_ci = 207
    utf8_persian_ci = 208
    utf8_esperanto_ci = 209
    utf8_hungarian_ci = 210
    utf8_sinhala_ci = 211
    utf8_german2_ci = 212
    utf8_croatian_ci = 213
    utf8_unicode_520_ci = 214
    utf8_vietnamese_ci = 215
    utf8_general_mysql500_ci = 223
    utf8mb4_unicode_ci = 224
    utf8mb4_icelandic_ci = 225
    utf8mb4_latvian_ci = 226
    utf8mb4_romanian_ci = 227
    utf8mb4_slovenian_ci = 228
    utf8mb4_polish_ci = 229
    utf8mb4_estonian_ci = 230
    utf8mb4_spanish_ci = 231
    utf8mb4_swedish_ci = 232
    utf8mb4_turkish_ci = 233
    utf8mb4_czech_ci = 234
    utf8mb4_danish_ci = 235
    utf8mb4_lithuanian_ci = 236
    utf8mb4_slovak_ci = 237
    utf8mb4_spanish2_ci = 238
    utf8mb4_roman_ci = 239
    utf8mb4_persian_ci = 240
    utf8mb4_esperanto_ci = 241
    utf8mb4_hungarian_ci = 242
    utf8mb4_sinhala_ci = 243
    utf8mb4_german2_ci = 244
    utf8mb4_croatian_ci = 245
    utf8mb4_unicode_520_ci = 246
    utf8mb4_vietnamese_ci = 247
    gb18030_chinese_ci = 248
    gb18030_bin = 249
    gb18030_unicode_520_ci = 250
    utf8mb4_0900_ai_ci = 255

    @property
    def codec(self) -> str:
        return self.charset.codec

    @property
    def charset(self) -> CharacterSet:
        return DEFAULT_CHARACTER_SETS[self]


DEFAULT_CHARACTER_SETS = {
    Collation.big5_chinese_ci: CharacterSet.big5,
    Collation.latin2_czech_cs: CharacterSet.latin2,
    Collation.dec8_swedish_ci: CharacterSet.dec8,
    Collation.cp850_general_ci: CharacterSet.cp850,
    Collation.latin1_german1_ci: CharacterSet.latin1,
    Collation.hp8_english_ci: CharacterSet.hp8,
    Collation.koi8r_general_ci: CharacterSet.koi8r,
    Collation.latin1_swedish_ci: CharacterSet.latin1,
    Collation.latin2_general_ci: CharacterSet.latin2,
    Collation.swe7_swedish_ci: CharacterSet.swe7,
    Collation.ascii_general_ci: CharacterSet.ascii,
    Collation.ujis_japanese_ci: CharacterSet.ujis,
    Collation.sjis_japanese_ci: CharacterSet.sjis,
    Collation.cp1251_bulgarian_ci: CharacterSet.cp1251,
    Collation.latin1_danish_ci: CharacterSet.latin1,
    Collation.hebrew_general_ci: CharacterSet.hebrew,
    Collation.tis620_thai_ci: CharacterSet.tis620,
    Collation.euckr_korean_ci: CharacterSet.euckr,
    Collation.latin7_estonian_cs: CharacterSet.latin7,
    Collation.latin2_hungarian_ci: CharacterSet.latin2,
    Collation.koi8u_general_ci: CharacterSet.koi8u,
    Collation.cp1251_ukrainian_ci: CharacterSet.cp1251,
    Collation.gb2312_chinese_ci: CharacterSet.gb2312,
    Collation.greek_general_ci: CharacterSet.greek,
    Collation.cp1250_general_ci: CharacterSet.cp1250,
    Collation.latin2_croatian_ci: CharacterSet.latin2,
    Collation.gbk_chinese_ci: CharacterSet.gbk,
    Collation.cp1257_lithuanian_ci: CharacterSet.cp1257,
    Collation.latin5_turkish_ci: CharacterSet.latin5,
    Collation.latin1_german2_ci: CharacterSet.latin1,
    Collation.armscii8_general_ci: CharacterSet.armscii8,
    Collation.utf8_general_ci: CharacterSet.utf8,
    Collation.cp1250_czech_cs: CharacterSet.cp1250,
    Collation.ucs2_general_ci: CharacterSet.ucs2,
    Collation.cp866_general_ci: CharacterSet.cp866,
    Collation.keybcs2_general_ci: CharacterSet.keybcs2,
    Collation.macce_general_ci: CharacterSet.macce,
    Collation.macroman_general_ci: CharacterSet.macroman,
    Collation.cp852_general_ci: CharacterSet.cp852,
    Collation.latin7_general_ci: CharacterSet.latin7,
    Collation.latin7_general_cs: CharacterSet.latin7,
    Collation.macce_bin: CharacterSet.macce,
    Collation.cp1250_croatian_ci: CharacterSet.cp1250,
    Collation.utf8mb4_general_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_bin: CharacterSet.utf8mb4,
    Collation.latin1_bin: CharacterSet.latin1,
    Collation.latin1_general_ci: CharacterSet.latin1,
    Collation.latin1_general_cs: CharacterSet.latin1,
    Collation.cp1251_bin: CharacterSet.cp1251,
    Collation.cp1251_general_ci: CharacterSet.cp1251,
    Collation.cp1251_general_cs: CharacterSet.cp1251,
    Collation.macroman_bin: CharacterSet.macroman,
    Collation.utf16_general_ci: CharacterSet.utf16,
    Collation.utf16_bin: CharacterSet.utf16,
    Collation.utf16le_general_ci: CharacterSet.utf16le,
    Collation.cp1256_general_ci: CharacterSet.cp1256,
    Collation.cp1257_bin: CharacterSet.cp1257,
    Collation.cp1257_general_ci: CharacterSet.cp1257,
    Collation.utf32_general_ci: CharacterSet.utf32,
    Collation.utf32_bin: CharacterSet.utf32,
    Collation.utf16le_bin: CharacterSet.utf16le,
    Collation.binary: CharacterSet.binary,
    Collation.armscii8_bin: CharacterSet.armscii8,
    Collation.ascii_bin: CharacterSet.ascii,
    Collation.cp1250_bin: CharacterSet.cp1250,
    Collation.cp1256_bin: CharacterSet.cp1256,
    Collation.cp866_bin: CharacterSet.cp866,
    Collation.dec8_bin: CharacterSet.dec8,
    Collation.greek_bin: CharacterSet.greek,
    Collation.hebrew_bin: CharacterSet.hebrew,
    Collation.hp8_bin: CharacterSet.hp8,
    Collation.keybcs2_bin: CharacterSet.keybcs2,
    Collation.koi8r_bin: CharacterSet.koi8r,
    Collation.koi8u_bin: CharacterSet.koi8u,
    Collation.latin2_bin: CharacterSet.latin2,
    Collation.latin5_bin: CharacterSet.latin5,
    Collation.latin7_bin: CharacterSet.latin7,
    Collation.cp850_bin: CharacterSet.cp850,
    Collation.cp852_bin: CharacterSet.cp852,
    Collation.swe7_bin: CharacterSet.swe7,
    Collation.utf8_bin: CharacterSet.utf8,
    Collation.big5_bin: CharacterSet.big5,
    Collation.euckr_bin: CharacterSet.euckr,
    Collation.gb2312_bin: CharacterSet.gb2312,
    Collation.gbk_bin: CharacterSet.gbk,
    Collation.sjis_bin: CharacterSet.sjis,
    Collation.tis620_bin: CharacterSet.tis620,
    Collation.ucs2_bin: CharacterSet.ucs2,
    Collation.ujis_bin: CharacterSet.ujis,
    Collation.geostd8_general_ci: CharacterSet.geostd8,
    Collation.geostd8_bin: CharacterSet.geostd8,
    Collation.latin1_spanish_ci: CharacterSet.latin1,
    Collation.cp932_japanese_ci: CharacterSet.cp932,
    Collation.cp932_bin: CharacterSet.cp932,
    Collation.eucjpms_japanese_ci: CharacterSet.eucjpms,
    Collation.eucjpms_bin: CharacterSet.eucjpms,
    Collation.cp1250_polish_ci: CharacterSet.cp1250,
    Collation.utf16_unicode_ci: CharacterSet.utf16,
    Collation.utf16_icelandic_ci: CharacterSet.utf16,
    Collation.utf16_latvian_ci: CharacterSet.utf16,
    Collation.utf16_romanian_ci: CharacterSet.utf16,
    Collation.utf16_slovenian_ci: CharacterSet.utf16,
    Collation.utf16_polish_ci: CharacterSet.utf16,
    Collation.utf16_estonian_ci: CharacterSet.utf16,
    Collation.utf16_spanish_ci: CharacterSet.utf16,
    Collation.utf16_swedish_ci: CharacterSet.utf16,
    Collation.utf16_turkish_ci: CharacterSet.utf16,
    Collation.utf16_czech_ci: CharacterSet.utf16,
    Collation.utf16_danish_ci: CharacterSet.utf16,
    Collation.utf16_lithuanian_ci: CharacterSet.utf16,
    Collation.utf16_slovak_ci: CharacterSet.utf16,
    Collation.utf16_spanish2_ci: CharacterSet.utf16,
    Collation.utf16_roman_ci: CharacterSet.utf16,
    Collation.utf16_persian_ci: CharacterSet.utf16,
    Collation.utf16_esperanto_ci: CharacterSet.utf16,
    Collation.utf16_hungarian_ci: CharacterSet.utf16,
    Collation.utf16_sinhala_ci: CharacterSet.utf16,
    Collation.utf16_german2_ci: CharacterSet.utf16,
    Collation.utf16_croatian_ci: CharacterSet.utf16,
    Collation.utf16_unicode_520_ci: CharacterSet.utf16,
    Collation.utf16_vietnamese_ci: CharacterSet.utf16,
    Collation.ucs2_unicode_ci: CharacterSet.ucs2,
    Collation.ucs2_icelandic_ci: CharacterSet.ucs2,
    Collation.ucs2_latvian_ci: CharacterSet.ucs2,
    Collation.ucs2_romanian_ci: CharacterSet.ucs2,
    Collation.ucs2_slovenian_ci: CharacterSet.ucs2,
    Collation.ucs2_polish_ci: CharacterSet.ucs2,
    Collation.ucs2_estonian_ci: CharacterSet.ucs2,
    Collation.ucs2_spanish_ci: CharacterSet.ucs2,
    Collation.ucs2_swedish_ci: CharacterSet.ucs2,
    Collation.ucs2_turkish_ci: CharacterSet.ucs2,
    Collation.ucs2_czech_ci: CharacterSet.ucs2,
    Collation.ucs2_danish_ci: CharacterSet.ucs2,
    Collation.ucs2_lithuanian_ci: CharacterSet.ucs2,
    Collation.ucs2_slovak_ci: CharacterSet.ucs2,
    Collation.ucs2_spanish2_ci: CharacterSet.ucs2,
    Collation.ucs2_roman_ci: CharacterSet.ucs2,
    Collation.ucs2_persian_ci: CharacterSet.ucs2,
    Collation.ucs2_esperanto_ci: CharacterSet.ucs2,
    Collation.ucs2_hungarian_ci: CharacterSet.ucs2,
    Collation.ucs2_sinhala_ci: CharacterSet.ucs2,
    Collation.ucs2_german2_ci: CharacterSet.ucs2,
    Collation.ucs2_croatian_ci: CharacterSet.ucs2,
    Collation.ucs2_unicode_520_ci: CharacterSet.ucs2,
    Collation.ucs2_vietnamese_ci: CharacterSet.ucs2,
    Collation.ucs2_general_mysql500_ci: CharacterSet.ucs2,
    Collation.utf32_unicode_ci: CharacterSet.utf32,
    Collation.utf32_icelandic_ci: CharacterSet.utf32,
    Collation.utf32_latvian_ci: CharacterSet.utf32,
    Collation.utf32_romanian_ci: CharacterSet.utf32,
    Collation.utf32_slovenian_ci: CharacterSet.utf32,
    Collation.utf32_polish_ci: CharacterSet.utf32,
    Collation.utf32_estonian_ci: CharacterSet.utf32,
    Collation.utf32_spanish_ci: CharacterSet.utf32,
    Collation.utf32_swedish_ci: CharacterSet.utf32,
    Collation.utf32_turkish_ci: CharacterSet.utf32,
    Collation.utf32_czech_ci: CharacterSet.utf32,
    Collation.utf32_danish_ci: CharacterSet.utf32,
    Collation.utf32_lithuanian_ci: CharacterSet.utf32,
    Collation.utf32_slovak_ci: CharacterSet.utf32,
    Collation.utf32_spanish2_ci: CharacterSet.utf32,
    Collation.utf32_roman_ci: CharacterSet.utf32,
    Collation.utf32_persian_ci: CharacterSet.utf32,
    Collation.utf32_esperanto_ci: CharacterSet.utf32,
    Collation.utf32_hungarian_ci: CharacterSet.utf32,
    Collation.utf32_sinhala_ci: CharacterSet.utf32,
    Collation.utf32_german2_ci: CharacterSet.utf32,
    Collation.utf32_croatian_ci: CharacterSet.utf32,
    Collation.utf32_unicode_520_ci: CharacterSet.utf32,
    Collation.utf32_vietnamese_ci: CharacterSet.utf32,
    Collation.utf8_unicode_ci: CharacterSet.utf8,
    Collation.utf8_icelandic_ci: CharacterSet.utf8,
    Collation.utf8_latvian_ci: CharacterSet.utf8,
    Collation.utf8_romanian_ci: CharacterSet.utf8,
    Collation.utf8_slovenian_ci: CharacterSet.utf8,
    Collation.utf8_polish_ci: CharacterSet.utf8,
    Collation.utf8_estonian_ci: CharacterSet.utf8,
    Collation.utf8_spanish_ci: CharacterSet.utf8,
    Collation.utf8_swedish_ci: CharacterSet.utf8,
    Collation.utf8_turkish_ci: CharacterSet.utf8,
    Collation.utf8_czech_ci: CharacterSet.utf8,
    Collation.utf8_danish_ci: CharacterSet.utf8,
    Collation.utf8_lithuanian_ci: CharacterSet.utf8,
    Collation.utf8_slovak_ci: CharacterSet.utf8,
    Collation.utf8_spanish2_ci: CharacterSet.utf8,
    Collation.utf8_roman_ci: CharacterSet.utf8,
    Collation.utf8_persian_ci: CharacterSet.utf8,
    Collation.utf8_esperanto_ci: CharacterSet.utf8,
    Collation.utf8_hungarian_ci: CharacterSet.utf8,
    Collation.utf8_sinhala_ci: CharacterSet.utf8,
    Collation.utf8_german2_ci: CharacterSet.utf8,
    Collation.utf8_croatian_ci: CharacterSet.utf8,
    Collation.utf8_unicode_520_ci: CharacterSet.utf8,
    Collation.utf8_vietnamese_ci: CharacterSet.utf8,
    Collation.utf8_general_mysql500_ci: CharacterSet.utf8,
    Collation.utf8mb4_unicode_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_icelandic_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_latvian_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_romanian_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_slovenian_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_polish_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_estonian_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_spanish_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_swedish_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_turkish_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_czech_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_danish_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_lithuanian_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_slovak_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_spanish2_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_roman_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_persian_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_esperanto_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_hungarian_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_sinhala_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_german2_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_croatian_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_unicode_520_ci: CharacterSet.utf8mb4,
    Collation.utf8mb4_vietnamese_ci: CharacterSet.utf8mb4,
    Collation.gb18030_chinese_ci: CharacterSet.gb18030,
    Collation.gb18030_bin: CharacterSet.gb18030,
    Collation.gb18030_unicode_520_ci: CharacterSet.gb18030,
    Collation.utf8mb4_0900_ai_ci: CharacterSet.utf8mb4,
}
DEFAULT_COLLATIONS = {
    CharacterSet.big5: Collation.big5_chinese_ci,
    CharacterSet.dec8: Collation.dec8_swedish_ci,
    CharacterSet.cp850: Collation.cp850_general_ci,
    CharacterSet.hp8: Collation.hp8_english_ci,
    CharacterSet.koi8r: Collation.koi8r_general_ci,
    CharacterSet.latin1: Collation.latin1_swedish_ci,
    CharacterSet.latin2: Collation.latin2_general_ci,
    CharacterSet.swe7: Collation.swe7_swedish_ci,
    CharacterSet.ascii: Collation.ascii_general_ci,
    CharacterSet.ujis: Collation.ujis_japanese_ci,
    CharacterSet.sjis: Collation.sjis_japanese_ci,
    CharacterSet.hebrew: Collation.hebrew_general_ci,
    CharacterSet.tis620: Collation.tis620_thai_ci,
    CharacterSet.euckr: Collation.euckr_korean_ci,
    CharacterSet.koi8u: Collation.koi8u_general_ci,
    CharacterSet.gb2312: Collation.gb2312_chinese_ci,
    CharacterSet.greek: Collation.greek_general_ci,
    CharacterSet.cp1250: Collation.cp1250_general_ci,
    CharacterSet.gbk: Collation.gbk_chinese_ci,
    CharacterSet.latin5: Collation.latin5_turkish_ci,
    CharacterSet.armscii8: Collation.armscii8_general_ci,
    CharacterSet.utf8: Collation.utf8_general_ci,
    CharacterSet.ucs2: Collation.ucs2_general_ci,
    CharacterSet.cp866: Collation.cp866_general_ci,
    CharacterSet.keybcs2: Collation.keybcs2_general_ci,
    CharacterSet.macce: Collation.macce_general_ci,
    CharacterSet.macroman: Collation.macroman_general_ci,
    CharacterSet.cp852: Collation.cp852_general_ci,
    CharacterSet.latin7: Collation.latin7_general_ci,
    CharacterSet.utf8mb4: Collation.utf8mb4_general_ci,
    CharacterSet.cp1251: Collation.cp1251_general_ci,
    CharacterSet.utf16: Collation.utf16_general_ci,
    CharacterSet.utf16le: Collation.utf16le_general_ci,
    CharacterSet.cp1256: Collation.cp1256_general_ci,
    CharacterSet.cp1257: Collation.cp1257_general_ci,
    CharacterSet.utf32: Collation.utf32_general_ci,
    CharacterSet.binary: Collation.binary,
    CharacterSet.geostd8: Collation.geostd8_general_ci,
    CharacterSet.cp932: Collation.cp932_japanese_ci,
    CharacterSet.eucjpms: Collation.eucjpms_japanese_ci,
    CharacterSet.gb18030: Collation.gb18030_chinese_ci,
}
