/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/crob.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    This program is free software; you can redistribute it and/or modify
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

typedef struct
{
    double crob_top, crob_bottom;
    double crob_left, crob_right;
    double crob_top_border, crob_bottom_border;
    double crob_left_border, crob_right_border;
    int crob_blur;
    double crob_ratioBlur;
    double crob_directBlur;
    double xInterval, yInterval;
    double xInt_2, yInt_2, minInt_2;
    double x0, y0, x0c, y0c;
    double setProb, setProbH, setProbQ, setProbTQ;
    double setCompProb, setCompProbH, setCompProbQ, setCompProbTQ;
    int    boolean;
} Variables;

// (SDK header apoplugin.h implied)


APO_PLUGIN("crob");

APO_VARIABLES(
    VAR_REAL(crob_top, -1.0),
    VAR_REAL(crob_bottom, 1.0),
    VAR_REAL(crob_left, -1.0),
    VAR_REAL(crob_right, 1.0),
    VAR_INTEGER(crob_blur, 1),
    VAR_REAL_RANGE(crob_ratioBlur, 0.0, 1.0, 0.05),
    VAR_REAL(crob_directBlur, 2.0)
);

int PluginVarPrepare(Variation* vp)
{
    double tmp;
    
    // ***** Preventing bad inputs *****
    if(VAR(crob_top)>VAR(crob_bottom))
    {
        tmp = VAR(crob_top);
        VAR(crob_top)    = VAR(crob_bottom);
        VAR(crob_bottom) = tmp;
    }
    if(VAR(crob_top)==VAR(crob_bottom))
    {
        VAR(crob_top)    = -1.0;
        VAR(crob_bottom) = 1.0;
    }
    if(VAR(crob_left)>VAR(crob_right))
    {
        tmp = VAR(crob_left);
        VAR(crob_left)  = VAR(crob_right);
        VAR(crob_right) = tmp;
    }
    if(VAR(crob_left)==VAR(crob_right))
    {
        VAR(crob_left)  = -1.0;
        VAR(crob_right) = 1.0;
    }
    if(VAR(crob_directBlur)<0.0) VAR(crob_directBlur) = 0.0;
    
    // ***** Initializing intervals *****
    if(VAR(crob_blur)!=0) VAR(crob_blur) = 1;
    VAR(xInterval) = fabs(VAR(crob_right) - VAR(crob_left));
    VAR(yInterval) = fabs(VAR(crob_bottom) - VAR(crob_top));
    VAR(xInt_2)    = VAR(xInterval)/2.0;
    VAR(yInt_2)    = VAR(yInterval)/2.0;
    if(VAR(xInt_2)>VAR(yInt_2)) VAR(minInt_2) = VAR(yInt_2);
    else                        VAR(minInt_2) = VAR(xInt_2);
    VAR(x0) = VAR(crob_right) - VAR(xInt_2);
    VAR(y0) = VAR(crob_top)   + VAR(yInt_2);
    
    // ***** Initializing reference point *****
    if(VAR(xInt_2)>VAR(yInt_2))
    {
        VAR(x0c) = VAR(crob_right) - VAR(minInt_2);
        VAR(y0c) = VAR(y0);
    }
    else if(VAR(xInt_2)<VAR(yInt_2))
    {
        VAR(x0c) = VAR(x0);
        VAR(y0c) = VAR(crob_top)  + VAR(minInt_2);
    }
    else
    {
        VAR(x0c) = VAR(x0);
        VAR(y0c) = VAR(y0);
    }
    
    // ***** Initializing probabilities *****
    VAR(setProb)   = VAR(yInterval)/(VAR(xInterval)+VAR(yInterval));
    VAR(setProbQ)  = 0.25*VAR(setProb);
    VAR(setProbH)  = 0.50*VAR(setProb);
    VAR(setProbTQ) = 0.75*VAR(setProb);
    VAR(setCompProb)   = 1.0 - VAR(setProb);
    VAR(setCompProbQ)  = VAR(setProb) + 0.25*VAR(setCompProb);
    VAR(setCompProbH)  = VAR(setProb) + 0.50*VAR(setCompProb);
    VAR(setCompProbTQ) = VAR(setProb) + 0.75*VAR(setCompProb);
    
    // ***** Defining inner area *****
    if(!VAR(boolean))
    {
        VAR(crob_top_border)    = VAR(crob_top)    + VAR(minInt_2)*VAR(crob_ratioBlur);
        VAR(crob_bottom_border) = VAR(crob_bottom) - VAR(minInt_2)*VAR(crob_ratioBlur); 
        VAR(crob_left_border)   = VAR(crob_left)   + VAR(minInt_2)*VAR(crob_ratioBlur);
        VAR(crob_right_border)  = VAR(crob_right)  - VAR(minInt_2)*VAR(crob_ratioBlur);
    }
    if(VAR(crob_blur==0))
    {
        VAR(crob_top_border)    = VAR(crob_top);
        VAR(crob_bottom_border) = VAR(crob_bottom); 
        VAR(crob_left_border)   = VAR(crob_left);
        VAR(crob_right_border)  = VAR(crob_right);                
    }
    
    VAR(boolean) = 1;
    
    return TRUE; 
}

int PluginVarCalc(Variation* vp)
{
    double gradTmp, secTmp, xTmp, yTmp;
    
    if((FTx<VAR(crob_left_border))||(FTx>VAR(crob_right_border))||(FTy<VAR(crob_top_border))||(FTy>VAR(crob_bottom_border)))
    {
        // ***** Case: no edge *****
        if(VAR(crob_blur)==0)
        {
            FTx = 0.0;
            FTy = 0.0;
        }
        // ***** Case: with edge *****
        else
        {
            secTmp = random01();
            
            // ***** Drawing top and bottom *****
            if(secTmp<VAR(setProb))
            {
                void setBlurPointsSec1()
                {
                    yTmp = VAR(crob_top)   + random01() * VAR(yInt_2);
                    xTmp = VAR(crob_right) - pow(random01(),VAR(crob_directBlur)) * VAR(crob_ratioBlur) * VAR(minInt_2);
                }
                
                int testBlurPointsSec1()
                {
                    gradTmp = (yTmp-VAR(y0c))/(xTmp-VAR(x0c));
                    if(gradTmp<-1.0) return FALSE;
                    else             return TRUE;
                }
                
                setBlurPointsSec1();
                while(testBlurPointsSec1()==FALSE) setBlurPointsSec1();
                
                if(secTmp<VAR(setProbH))                            xTmp = VAR(crob_left) + VAR(crob_right) - xTmp;
                if((secTmp>VAR(setProbQ))&&(secTmp<VAR(setProbTQ))) yTmp = VAR(crob_bottom) + VAR(crob_top) - yTmp;
            }
            // ***** Drawing left and right *****
            else
            {
                void setBlurPointsSec2()
                {
                    xTmp = VAR(crob_right) - random01() * VAR(xInt_2);
                    yTmp = VAR(crob_top)   + pow(random01(),VAR(crob_directBlur)) * VAR(crob_ratioBlur) * VAR(minInt_2);
                }
                
                int testBlurPointsSec2()
                {
                    gradTmp = (yTmp-VAR(y0c))/(xTmp-VAR(x0c));
                    if(!(gradTmp>0.0)&&(gradTmp>-1.0)) return FALSE;
                    else                               return TRUE;
                }
                
                setBlurPointsSec2();
                while(testBlurPointsSec2()==FALSE) setBlurPointsSec2();
                
                if(secTmp>VAR(setCompProbH))                                yTmp = VAR(crob_bottom) + VAR(crob_top) - yTmp;
                if((secTmp>VAR(setCompProbQ))&&(secTmp<VAR(setCompProbTQ))) xTmp = VAR(crob_left) + VAR(crob_right) - xTmp;
            }
            
            // ***** Allocating values *****
            FTx = xTmp;
            FTy = yTmp;    
        }
    }
    
    FPx += FTx;
    FPy += FTy;

    return TRUE;
}
