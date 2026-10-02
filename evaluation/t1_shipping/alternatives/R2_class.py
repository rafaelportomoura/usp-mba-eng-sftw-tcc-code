# EVALUATION-ONLY: variante de avaliacao; nao fornecer ao agente avaliado.

import math
class _Calc:
    BASE = dict(local=850, regional=1550, national=2490)
    def __init__(self, w, d, s, e):
        for v in (w, s):
            if isinstance(v, bool): raise ValueError
        if not isinstance(w,(int,float)) or not (w>0 and w<=30): raise ValueError
        if not isinstance(d,str) or d.strip().lower() not in self.BASE: raise ValueError
        if not isinstance(s,int) or s<0: raise ValueError
        if not isinstance(e,bool): raise ValueError
        self.w,self.d,self.s,self.e=w,d.strip().lower(),s,e
    def run(self):
        std = self.BASE[self.d] + max(0, math.ceil(self.w)-1)*200
        total = 0 if self.s>=20000 else std
        if self.e:
            total += max(1000, int(std*25/100 + 0.5) if std%4 != 2 else (std*25+50)//100)
        return total
def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    return _Calc(weight_kg, destination, subtotal_cents, express).run()
