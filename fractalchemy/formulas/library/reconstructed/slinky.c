/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        slinky.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from slinky.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int slinky_case;
    double slinky_r;
    double slinky_n;
    double slinky_a;
    double slinky_h;
    double slinky_rr;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("slinky");
APO_VARIABLES(
    VAR_INTEGER(slinky_case, 32),
    VAR_REAL(slinky_r, 1.0),
    VAR_REAL(slinky_n, 1.0),
    VAR_REAL(slinky_a, 1.0),
    VAR_REAL(slinky_h, 1.0),
    VAR_REAL(slinky_rr, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cos(FTy);
    double t2 = sin(FTx);
    double t3 = FTx * VAR(slinky_h);
    double t4 = t2 + t3;
    double t5 = cos(FTx);
    double t6 = t4 * t5;
    double t7 = t1 * t6;
    double t8 = sin(FTy);
    double t9 = t4 * t8;
    double t10 = t1 * t9;
    double t11 = t4 * FTy;
    double t12 = t7 * t7 + t10 * t10 + t11 * t11 + 1e-20;
    double t13 = 10.0 - VAR(slinky_rr);
    double t14 = t6 * t6 + t9 * t9 + t4 * t4 + 1e-20;
    double t15 = t1 + VAR(slinky_r);
    double t16 = t15 * t5;
    double t17 = t15 * t2;
    double t18 = cos(t17);
    double t19 = sin(t16) * t18;
    double t20 = FTx * VAR(slinky_n);
    double t21 = FTx * FTx;
    double t22 = t21 + FTy * FTy;
    double t23 = sqrt(t22);
    double t24 = atan2(FTy, FTx);
    double t25 = t19 * cos(tan(t20 / t23) / t24);
    double t26 = cos(t16);
    double t27 = t26 * t18;
    double t28 = FTy * VAR(slinky_n);
    double t29 = tan(t28 / t23) / t24;
    double t30 = t27 * cos(t29);
    double t31 = FTy * VAR(slinky_h);
    double t32 = sin(t17);
    double t33 = t31 + t32 + VAR(slinky_a) * sin(t29);
    double t34 = t25 * t25 + t30 * t30 + t33 * t33 + 1e-20;
    double t35 = t19 * t19 + t27 * t27 + t32 * t32 + 1e-20;
    double t36 = tan(FTx / t23) / t24;
    double t37 = t36 * t16;
    double t38 = tan(FTy / t23) / t24;
    double t39 = t38 * t17;
    double t40 = (tan(FTz / t23) / t24) * t8;
    double t41 = t37 * t37 + t39 * t39 + t40 * t40 + 1e-20;
    double t42 = t26 * (cos(VAR(slinky_n) * t16) * VAR(slinky_a) + VAR(slinky_r));
    double t43 = t42 + t16;
    double t44 = t32 * (cos(VAR(slinky_n) * t17) * VAR(slinky_a) + VAR(slinky_r));
    double t45 = t44 + t17;
    double t46 = sin(VAR(slinky_n) * t8) * VAR(slinky_a) + VAR(slinky_h) * t8;
    double t47 = t46 + t8;
    double t48 = t43 * t43 + t45 * t45 + t47 * t47 + 1e-20;
    double t49 = t42 * t42 + t44 * t44 + t46 * t46 + 1e-20;
    double t50 = cos(t28 + 1.0) + VAR(slinky_r);
    double t51 = FTx + 1.0;
    double t52 = cos(t28);
    double t53 = t52 + VAR(slinky_r);
    double t54 = t53 * t5;
    double t55 = (t50 * cos(t51) + t54) / 2.0;
    double t56 = t55 + t36;
    double t57 = sin(t36);
    double t58 = cos(t38);
    double t59 = t56 * (t57 * t58);
    double t60 = t53 * t2;
    double t61 = (t50 * sin(t51) + t60) / 2.0;
    double t62 = t61 + t38;
    double t63 = cos(t36);
    double t64 = t62 * (t63 * t58);
    double t65 = (sin(M_PI * FTz) + VAR(slinky_r) + sin(FTz * VAR(slinky_n)) * VAR(slinky_a)) / 2.0 + t31;
    double t66 = t65 * t65;
    double t67 = t59 * t59 + t64 * t64 + t66 + 1e-20;
    double t68 = VAR(slinky_rr) * t65;
    double t69 = t13 * t65 / 10.0;
    double t70 = t56 * t56 + t62 * t62 + t66 + 1e-20;
    double t71 = sin(t28) * VAR(slinky_a) + t31;
    double t72 = sin(M_PI * FTy) + VAR(slinky_r) + t71;
    double t73 = t72 * t72;
    double t74 = t55 * t55 + t61 * t61 + t73 + 1e-20;
    double t75 = VAR(slinky_rr) * t72;
    double t76 = t13 * t72 / 10.0;
    double t77 = t54 * t54 + t60 * t60 + t73 + 1e-20;
    double t78 = t5 * t1;
    double t79 = t78 * t63 * t58;
    double t80 = t2 * t1;
    double t81 = t80 * t57 * t58;
    double t82 = t8 * sin(t38);
    double t83 = t79 * t79 + t81 * t81 + t82 * t82 + 1e-20;
    double t84 = tan(FTx) / t24;
    double t85 = cos(t84);
    double t86 = tan(FTy) / t24;
    double t87 = cos(t86);
    double t88 = t85 * t87;
    double t89 = VAR(slinky_rr) * t88;
    double t90 = t88 * t88;
    double t91 = sin(t84);
    double t92 = t91 * t87;
    double t93 = t90 + t92 * t92;
    double t94 = sin(t86);
    double t95 = t94 * t94;
    double t96 = t93 + t95 + 1e-20;
    double t97 = t13 * t88 / 10.0;
    double t98 = VAR(slinky_rr) * t92;
    double t99 = t13 * t92 / 10.0;
    double t100 = VAR(slinky_rr) * t94;
    double t101 = t13 * t94 / 10.0;
    double t102 = t8 * t8;
    double t103 = t93 + t102 + 1e-20;
    double t104 = VAR(slinky_rr) * t8;
    double t105 = t13 * t8 / 10.0;
    double t106 = t78 + t88;
    double t107 = VAR(slinky_rr) * t106;
    double t108 = t106 * t106;
    double t109 = t80 + t92;
    double t110 = t8 + t94;
    double t111 = t110 * t110;
    double t112 = t108 + t109 * t109 + t111 + 1e-20;
    double t113 = t13 * t106 / 10.0;
    double t114 = VAR(slinky_rr) * t110;
    double t115 = t13 * t110 / 10.0;
    double t116 = t78 * t85 * t87;
    double t117 = VAR(slinky_rr) * t116;
    double t118 = t116 * t116;
    double t119 = t80 * t91;
    double t120 = t119 * t87;
    double t121 = t8 * t94;
    double t122 = t121 * t121;
    double t123 = t118 + t120 * t120 + t122 + 1e-20;
    double t124 = t13 * t116 / 10.0;
    double t125 = VAR(slinky_rr) * t121;
    double t126 = t13 * t121 / 10.0;
    double t127 = t5 * t85 * t87;
    double t128 = t2 * t91 * t94;
    double t129 = t127 * t127 + t128 * t128 + t102 + 1e-20;
    double t130 = t1 * t85 * t87;
    double t131 = t1 * t91 * t94;
    double t132 = t130 * t130 + t131 * t131 + t102 + 1e-20;
    double t133 = t119 * t94;
    double t134 = t118 + t133 * t133 + t122 + 1e-20;
    double t135 = t91 * t94;
    double t136 = t90 + t135 * t135 + t95 + 1e-20;
    double t137 = t80 + t135;
    double t138 = t108 + t137 * t137 + t111 + 1e-20;
    double t139 = t1 * (cos(FTx * t85) * (cos(VAR(slinky_n) * t91) * VAR(slinky_a) + VAR(slinky_r)));
    double t140 = t1 * (sin(FTx * t87) * (cos(VAR(slinky_n) * t94) * VAR(slinky_a) + VAR(slinky_r)));
    double t141 = tan(FTz) / t24;
    double t142 = t2 * (sin(VAR(slinky_n) * sin(t141)) * VAR(slinky_a)) + t3;
    double t143 = t139 * t139 + t140 * t140 + t142 * t142 + 1e-20;
    double t144 = cos(t28 * t84) * VAR(slinky_a) + VAR(slinky_r);
    double t145 = t1 * (cos(FTx * t84) * t144);
    double t146 = VAR(slinky_rr) * t145;
    double t147 = cos(t28 * t86) * VAR(slinky_a) + VAR(slinky_r);
    double t148 = t1 * (sin(FTx * t86) * t147);
    double t149 = t145 * t145 + t148 * t148;
    double t150 = t2 * (sin(t20 * t141) * VAR(slinky_a)) + t3;
    double t151 = t150 * t150;
    double t152 = t149 + t151 + 1e-20;
    double t153 = t13 * t145 / 10.0;
    double t154 = VAR(slinky_rr) * t148;
    double t155 = t13 * t148 / 10.0;
    double t156 = VAR(slinky_rr) * t150;
    double t157 = t13 * t150 / 10.0;
    double t158 = t2 * (sin(t20 * t23) * VAR(slinky_a)) + t3;
    double t159 = t158 * t158;
    double t160 = t149 + t159 + 1e-20;
    double t161 = VAR(slinky_rr) * t158;
    double t162 = t13 * t158 / 10.0;
    double t163 = FTx * t23;
    double t164 = cos(t163);
    double t165 = t1 * (t164 * t144);
    double t166 = VAR(slinky_rr) * t165;
    double t167 = t165 * t165;
    double t168 = sin(t163);
    double t169 = t1 * (t168 * t147);
    double t170 = t167 + t169 * t169;
    double t171 = t170 + t159 + 1e-20;
    double t172 = t13 * t165 / 10.0;
    double t173 = VAR(slinky_rr) * t169;
    double t174 = t13 * t169 / 10.0;
    double t175 = t1 * (t168 * t144);
    double t176 = t167 + t175 * t175 + t159 + 1e-20;
    double t177 = t170 + t151 + 1e-20;
    double t178 = t28 * FTy;
    double t179 = cos(t178) * VAR(slinky_a) + VAR(slinky_r);
    double t180 = cos(t21) * t179;
    double t181 = sin(t21) * t179;
    double t182 = sin(t178) * VAR(slinky_a) + t31;
    double t183 = t180 * t180 + t181 * t181 + t182 * t182 + 1e-20;
    double t184 = random01();
    double t185 = t23 * t184;
    double t186 = VAR(slinky_n) * t185;
    double t187 = cos(t186) * VAR(slinky_a) + 1.0;
    double t188 = cos(t185) * t187;
    double t189 = sin(t185) * t187;
    double t190 = sin(t186) * VAR(slinky_a) + VAR(slinky_h) * t185;
    double t191 = t188 * t188 + t189 * t189 + t190 * t190 + 1e-20;
    double t192 = VAR(slinky_n) * t22;
    double t193 = cos(t192) * VAR(slinky_a) + 1.0;
    double t194 = cos(t22) * t193;
    double t195 = sin(t22) * t193;
    double t196 = sin(t192) * VAR(slinky_a) + VAR(slinky_h) * t22;
    double t197 = t194 * t194 + t195 * t195 + t196 * t196 + 1e-20;
    double t198 = t184 * VAR(slinky_r);
    double t199 = VAR(slinky_n) * t198;
    double t200 = cos(t199) * VAR(slinky_a) + 1.0;
    double t201 = cos(t198) * t200;
    double t202 = sin(t198) * t200;
    double t203 = sin(t199) * VAR(slinky_a) + VAR(slinky_h) * t198;
    double t204 = t201 * t201 + t202 * t202 + t203 * t203 + 1e-20;
    double t205 = t28 * t23;
    double t206 = cos(t205) * VAR(slinky_a) + VAR(slinky_r);
    double t207 = t164 * t206;
    double t208 = t168 * t206;
    double t209 = sin(t205) * VAR(slinky_a) + t31;
    double t210 = t207 * t207 + t208 * t208 + t209 * t209 + 1e-20;
    double t211 = t52 * VAR(slinky_a) + VAR(slinky_r);
    double t212 = t5 * t211;
    double t213 = t2 * t211;
    double t214 = t212 * t212 + t213 * t213 + t71 * t71 + 1e-20;
    double t215 = 0.0 /* uninitialised local */ * 0.0 /* uninitialised local */ + 0.0 /* uninitialised local */ * 0.0 /* uninitialised local */ + 0.0 /* uninitialised local */ * 0.0 /* uninitialised local */ + 1e-20;
    if (VAR(slinky_case) > 32) {
        FPx = (VAR(slinky_rr) * 0.0 /* uninitialised local */ / t215 + (t13 * 0.0 /* uninitialised local */ / 10.0)) * VVAR + FPx;
        FPy = (VAR(slinky_rr) * 0.0 /* uninitialised local */ / t215 + (t13 * 0.0 /* uninitialised local */ / 10.0)) * VVAR + FPy;
        FPz = (VAR(slinky_rr) * 0.0 /* uninitialised local */ / t215 + (t13 * 0.0 /* uninitialised local */ / 10.0)) * VVAR + FPz;
    } else {
        if (VAR(slinky_case) == 0) {
            FPx = (VAR(slinky_rr) * t212 / t214 + (t13 * t212 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t213 / t214 + (t13 * t213 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t71 / t214 + (t13 * t71 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 1) {
            FPx = (VAR(slinky_rr) * t207 / t210 + (t13 * t207 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t208 / t210 + (t13 * t208 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t209 / t210 + (t13 * t209 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 2) {
            FPx = (VAR(slinky_rr) * t201 / t204 + (t13 * t201 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t202 / t204 + (t13 * t202 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t203 / t204 + (t13 * t203 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 3) {
            FPx = (VAR(slinky_rr) * t194 / t197 + (t13 * t194 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t195 / t197 + (t13 * t195 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t196 / t197 + (t13 * t196 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 4) {
            FPx = (VAR(slinky_rr) * t188 / t191 + (t13 * t188 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t189 / t191 + (t13 * t189 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t190 / t191 + (t13 * t190 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 5) {
            FPx = (VAR(slinky_rr) * t180 / t183 + (t13 * t180 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t181 / t183 + (t13 * t181 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t182 / t183 + (t13 * t182 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 6) {
            FPx = (t166 / t177 + t172) * VVAR + FPx;
            FPy = (t173 / t177 + t174) * VVAR + FPy;
            FPz = (t156 / t177 + t157) * VVAR + FPz;
        } else if (VAR(slinky_case) == 7) {
            FPx = (t166 / t176 + t172) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t175 / t176 + (t13 * t175 / 10.0)) * VVAR + FPy;
            FPz = (t161 / t176 + t162) * VVAR + FPz;
        } else if (VAR(slinky_case) == 8) {
            FPx = (t166 / t171 + t172) * VVAR + FPx;
            FPy = (t173 / t171 + t174) * VVAR + FPy;
            FPz = (t161 / t171 + t162) * VVAR + FPz;
        } else if (VAR(slinky_case) == 9) {
            FPx = (t146 / t160 + t153) * VVAR + FPx;
            FPy = (t154 / t160 + t155) * VVAR + FPy;
            FPz = (t161 / t160 + t162) * VVAR + FPz;
        } else if (VAR(slinky_case) == 10) {
            FPx = (t146 / t152 + t153) * VVAR + FPx;
            FPy = (t154 / t152 + t155) * VVAR + FPy;
            FPz = (t156 / t152 + t157) * VVAR + FPz;
        } else if (VAR(slinky_case) == 11) {
            FPx = (VAR(slinky_rr) * t139 / t143 + (t13 * t139 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t140 / t143 + (t13 * t140 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t142 / t143 + (t13 * t142 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 12) {
            FPx = (t107 / t138 + t113) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t137 / t138 + (t13 * t137 / 10.0)) * VVAR + FPy;
            FPz = (t114 / t138 + t115) * VVAR + FPz;
        } else if (VAR(slinky_case) == 13) {
            FPx = (t89 / t136 + t97) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t135 / t136 + (t13 * t135 / 10.0)) * VVAR + FPy;
            FPz = (t100 / t136 + t101) * VVAR + FPz;
        } else if (VAR(slinky_case) == 14) {
            FPx = (t117 / t134 + t124) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t133 / t134 + (t13 * t133 / 10.0)) * VVAR + FPy;
            FPz = (t125 / t134 + t126) * VVAR + FPz;
        } else if (VAR(slinky_case) == 15) {
            FPx = (VAR(slinky_rr) * t130 / t132 + (t13 * t130 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t131 / t132 + (t13 * t131 / 10.0)) * VVAR + FPy;
            FPz = (t104 / t132 + t105) * VVAR + FPz;
        } else if (VAR(slinky_case) == 16) {
            FPx = (VAR(slinky_rr) * t127 / t129 + (t13 * t127 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t128 / t129 + (t13 * t128 / 10.0)) * VVAR + FPy;
            FPz = (t104 / t129 + t105) * VVAR + FPz;
        } else if (VAR(slinky_case) == 17) {
            FPx = (t117 / t123 + t124) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t120 / t123 + (t13 * t120 / 10.0)) * VVAR + FPy;
            FPz = (t125 / t123 + t126) * VVAR + FPz;
        } else if (VAR(slinky_case) == 18) {
            FPx = (t107 / t112 + t113) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t109 / t112 + (t13 * t109 / 10.0)) * VVAR + FPy;
            FPz = (t114 / t112 + t115) * VVAR + FPz;
        } else if (VAR(slinky_case) == 19) {
            FPx = (t89 / t103 + t97) * VVAR + FPx;
            FPy = (t98 / t103 + t99) * VVAR + FPy;
            FPz = (t104 / t103 + t105) * VVAR + FPz;
        } else if (VAR(slinky_case) == 20) {
            FPx = (t89 / t96 + t97) * VVAR + FPx;
            FPy = (t98 / t96 + t99) * VVAR + FPy;
            FPz = (t100 / t96 + t101) * VVAR + FPz;
        } else if (VAR(slinky_case) == 21) {
            FPx = (VAR(slinky_rr) * t79 / t83 + (t13 * t79 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t81 / t83 + (t13 * t81 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t82 / t83 + (t13 * t82 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 22) {
            FPx = (VAR(slinky_rr) * t54 / t77 + (t13 * t54 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t60 / t77 + (t13 * t60 / 10.0)) * VVAR + FPy;
            FPz = (t75 / t77 + t76) * VVAR + FPz;
        } else if (VAR(slinky_case) == 23) {
            FPx = (VAR(slinky_rr) * t55 / t74 + (t13 * t55 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t61 / t74 + (t13 * t61 / 10.0)) * VVAR + FPy;
            FPz = (t75 / t74 + t76) * VVAR + FPz;
        } else if (VAR(slinky_case) == 24) {
            FPx = (VAR(slinky_rr) * t56 / t70 + (t13 * t56 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t62 / t70 + (t13 * t62 / 10.0)) * VVAR + FPy;
            FPz = (t68 / t70 + t69) * VVAR + FPz;
        } else if (VAR(slinky_case) == 25) {
            FPx = (VAR(slinky_rr) * t59 / t67 + (t13 * t59 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t64 / t67 + (t13 * t64 / 10.0)) * VVAR + FPy;
            FPz = (t68 / t67 + t69) * VVAR + FPz;
        } else if (VAR(slinky_case) == 26) {
            FPx = (VAR(slinky_rr) * t42 / t49 + (t13 * t42 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t44 / t49 + (t13 * t44 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t46 / t49 + (t13 * t46 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 27) {
            FPx = (VAR(slinky_rr) * t43 / t48 + (t13 * t43 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t45 / t48 + (t13 * t45 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t47 / t48 + (t13 * t47 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 28) {
            FPx = (VAR(slinky_rr) * t37 / t41 + (t13 * t37 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t39 / t41 + (t13 * t39 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t40 / t41 + (t13 * t40 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 29) {
            FPx = (VAR(slinky_rr) * t19 / t35 + (t13 * t19 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t27 / t35 + (t13 * t27 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t32 / t35 + (t13 * t32 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 30) {
            FPx = (VAR(slinky_rr) * t25 / t34 + (t13 * t25 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t30 / t34 + (t13 * t30 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t33 / t34 + (t13 * t33 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 31) {
            FPx = (VAR(slinky_rr) * t6 / t14 + (t13 * t6 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t9 / t14 + (t13 * t9 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t4 / t14 + (t13 * t4 / 10.0)) * VVAR + FPz;
        } else if (VAR(slinky_case) == 32) {
            FPx = (VAR(slinky_rr) * t7 / t12 + (t13 * t7 / 10.0)) * VVAR + FPx;
            FPy = (VAR(slinky_rr) * t10 / t12 + (t13 * t10 / 10.0)) * VVAR + FPy;
            FPz = (VAR(slinky_rr) * t11 / t12 + (t13 * t11 / 10.0)) * VVAR + FPz;
        }
    }
    return TRUE;
}