/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        exblur.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    exblur Apophysis Plugin
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
    double exblur_r, exblur_dist;
    double exblur_x_origin, exblur_y_origin, exblur_z_origin;

    int n; double r[4];
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("exblur");

APO_VARIABLES(
    VAR_REAL(exblur_dist, 0.5),
    VAR_REAL(exblur_r, 0.0),
    VAR_REAL(exblur_x_origin, 0.0),
    VAR_REAL(exblur_y_origin, 0.0),
    VAR_REAL(exblur_z_origin, 0.0),
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
    double r, theta, phi, su, cu, sv, cv, sru, cru, srv, crv, n, rsrv;
    double ox, oy, oz;

    ox = FPx - VAR(exblur_x_origin);
    oy = FPy + VAR(exblur_y_origin);
    oz = FPz - VAR(exblur_z_origin);
    n = sqr(ox) + sqr(oy) + sqr(oz);
    r = VVAR * pow(n, VAR(exblur_dist)) *
        (VAR(r)[0] + VAR(r)[1] + VAR(r)[2] + VAR(r)[3] - 2.0);
    theta = atan2(oy, ox);
    phi = acos(oz / sqrt(n));
    fsincos(theta, &su, &cu);
    fsincos(phi, &sv, &cv);
    fsincos(random01() * M_2PI, &sru, &cru);
    fsincos(random01() * M_2PI, &srv, &crv);
    VAR(r)[VAR(n)] = random01();
    VAR(n) = VAR(n) + 1 & 3;
    rsrv = VAR(exblur_r * srv);
    
    FPx += r * (sv * cu + rsrv * cru);
    FPy += r * (sv * su + rsrv * sru);
    FPz += r * (cv + VAR(exblur_r) * crv);
    
    return TRUE;
}
