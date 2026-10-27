/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        farblur.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    farblur Apophysis Plugin
    Copyright 2010 Branden Brown, a.k.a. zephyrtronium

    This plugin is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.

    This plugin is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this plugin; if not, see <http://www.gnu.org/licenses/>.
*/

typedef struct
{
    double farblur_x, farblur_y, farblur_z;
    double farblur_x_origin, farblur_y_origin, farblur_z_origin;

    unsigned char n;
    double r[4];
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("farblur");

APO_VARIABLES(
    VAR_REAL(farblur_x, 1.0),
    VAR_REAL(farblur_y, 1.0),
    VAR_REAL(farblur_z, 1.0),
    VAR_REAL(farblur_x_origin, 0.0),
    VAR_REAL(farblur_y_origin, 0.0),
    VAR_REAL(farblur_z_origin, 0.0),
);

int PluginVarPrepare(Variation* vp)
{
    VAR(n) = 0;
    VAR(r)[0] = random01();
    VAR(r)[1] = random01();
    VAR(r)[2] = random01();
    VAR(r)[3] = random01();

    return TRUE; 
}

int PluginVarCalc(Variation* vp)
{
    double r, su, cu, sv, cv;

    r = VVAR * (sqr(FPx - VAR(farblur_x_origin)) +
        sqr(FPy - VAR(farblur_y_origin)) +
        sqr(FPz - VAR(farblur_z_origin))) *
        (VAR(r)[0] + VAR(r)[1] + VAR(r)[2] + VAR(r)[3] - 2.0);
    VAR(r)[VAR(n)] = random01();
    VAR(n) = VAR(n) + 1 & 3;
    fsincos(random01() * M_2PI, &su, &cu);
    fsincos(random01() * M_2PI, &sv, &cv);

    FPx += VAR(farblur_x) * r * sv * cu;
    FPy += VAR(farblur_y) * r * sv * su;
    FPz += VAR(farblur_z) * r * cv;

    return TRUE;
}
