/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/MobiusN/MobiusN.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    This program is free software; you can redistribute it and/or MobiusNify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
*/

// Must define this structure before we include apoplugin.h
typedef struct
{
    double MobiusNRe_A, MobiusNIm_A, MobiusNRe_B, MobiusNIm_B, MobiusNRe_C, MobiusNIm_C, MobiusNRe_D, MobiusNIm_D ;
    double MobiusN_Power,MobiusN_Dist;

} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("MobiusN");


// Define the Variables
APO_VARIABLES(
    VAR_REAL(MobiusNRe_A, 1.0),
    VAR_REAL(MobiusNIm_A, 0.0),
    VAR_REAL(MobiusNRe_B, 0.0),
    VAR_REAL(MobiusNIm_B, 0.0),
    VAR_REAL(MobiusNRe_C, 0.0),
    VAR_REAL(MobiusNIm_C, 0.0),
    VAR_REAL(MobiusNRe_D, 1.0),
    VAR_REAL(MobiusNIm_D, 0.0),
    VAR_REAL(MobiusN_Power,2.0),
    VAR_REAL(MobiusN_Dist,1.0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    if (fabs(VAR(MobiusN_Power))<1.0) VAR(MobiusN_Power)=1.0;
    return TRUE; // Always return TRUE.
}



// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double MobiusNRe_U, MobiusNIm_U, MobiusNRe_V, MobiusNIm_V, Rad_V, X, Y, R, alpha, sina, cosa,z;
    int N;

    z=4*VAR(MobiusN_Dist)/VAR(MobiusN_Power); 
    R=pow(sqrt(sqr(FTx)+sqr(FTy)),z);

    alpha=atan2(FTy,FTx)*VAR(MobiusN_Power);
    fsincos(alpha,&sina,&cosa);
    X=R*cosa;
    Y=R*sina; 
    
    MobiusNRe_U = VAR(MobiusNRe_A) *X - VAR(MobiusNIm_A) *Y + VAR(MobiusNRe_B);
    MobiusNIm_U = VAR(MobiusNRe_A) *Y + VAR(MobiusNIm_A) *X + VAR(MobiusNIm_B);
    MobiusNRe_V = VAR(MobiusNRe_C) *X - VAR(MobiusNIm_C) *Y + VAR(MobiusNRe_D);
    MobiusNIm_V = VAR(MobiusNRe_C) *Y + VAR(MobiusNIm_C) *X + VAR(MobiusNIm_D);
    Rad_V= MobiusNRe_V * MobiusNRe_V + MobiusNIm_V * MobiusNIm_V;
    
    X= (MobiusNRe_U*MobiusNRe_V + MobiusNIm_U*MobiusNIm_V)/Rad_V;
    Y= (MobiusNIm_U*MobiusNRe_V - MobiusNRe_U*MobiusNIm_V)/Rad_V;
    

    z=1.0/z;
    R=pow(sqrt(sqr(X)+sqr(Y)),z);
    N=floor(VAR(MobiusN_Power)*random01());
    alpha=(atan2(Y,X)+N*M_2PI)/floor(VAR(MobiusN_Power));    
    fsincos(alpha,&sina,&cosa);
    
    FPx+=VVAR*R*cosa;
    FPy+=VVAR*R*sina;

    return TRUE;
}
