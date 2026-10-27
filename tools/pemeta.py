"""Extract Apophysis plugin metadata (name, variables with type/min/max/default) from a plugin DLL."""
import struct, re, sys, json, pathlib

class PE:
    def __init__(self, data):
        self.d = data
        pe = struct.unpack_from('<I', data, 0x3c)[0]
        assert data[pe:pe+4] == b'PE\0\0'
        self.machine, nsec, _, _, _, optsize, _ = struct.unpack_from('<HHIIIHH', data, pe + 4)
        opt = pe + 24
        magic = struct.unpack_from('<H', data, opt)[0]
        self.is64 = magic == 0x20b
        if self.is64:
            self.image_base = struct.unpack_from('<Q', data, opt + 24)[0]
            dd = opt + 112
        else:
            self.image_base = struct.unpack_from('<I', data, opt + 28)[0]
            dd = opt + 96
        self.export_rva, self.export_size = struct.unpack_from('<II', data, dd)
        self.sections = []
        s = opt + optsize
        for i in range(nsec):
            name, vsize, va, rawsize, rawptr = struct.unpack_from('<8sIIII', data, s + i * 40)
            self.sections.append((name.rstrip(b'\0').decode(errors='replace'), va, vsize, rawptr, rawsize))
    def rva2off(self, rva):
        for name, va, vsize, rawptr, rawsize in self.sections:
            if va <= rva < va + max(vsize, rawsize):
                return rawptr + (rva - va)
        raise ValueError('rva not mapped %x' % rva)
    def va2off(self, va):
        return self.rva2off(va - self.image_base)
    def cstr(self, off):
        end = self.d.index(b'\0', off)
        return self.d[off:end].decode(errors='replace')
    def exports(self):
        e = self.rva2off(self.export_rva)
        (_, _, _, _, name_rva, base, nfuncs, nnames, addr_rva, names_rva, ord_rva) = struct.unpack_from('<IIHHIIIIIII', self.d, e)
        out = {}
        for i in range(nnames):
            nrva = struct.unpack_from('<I', self.d, self.rva2off(names_rva) + 4 * i)[0]
            ordn = struct.unpack_from('<H', self.d, self.rva2off(ord_rva) + 2 * i)[0]
            frva = struct.unpack_from('<I', self.d, self.rva2off(addr_rva) + 4 * ordn)[0]
            out[self.cstr(self.rva2off(nrva))] = frva
        return out
    def u32(self, off): return struct.unpack_from('<I', self.d, off)[0]
    def i32(self, off): return struct.unpack_from('<i', self.d, off)[0]
    def u64(self, off): return struct.unpack_from('<Q', self.d, off)[0]
    def f64(self, off): return struct.unpack_from('<d', self.d, off)[0]
    def ptr(self, off): return self.u64(off) if self.is64 else self.u32(off)

def find_global_load(pe, frva, want_lea=False):
    """Scan the first bytes of a function for absolute/rip-relative data references; returns [(pos, VA, opcode)]."""
    off = pe.rva2off(frva)
    code = pe.d[off:off + 160]
    cands = []
    if pe.is64:
        pats = [rb'\x48\x8b\x05', rb'\x48\x8d\x05', rb'\x8b\x05', rb'\x48\x8b\x0d', rb'\x48\x8d\x0d', rb'\x8b\x0d', rb'\x48\x8d\x15', rb'\x48\x8b\x15', rb'\x3b\x05', rb'\x48\x8d\x1d', rb'\x48\x8b\x1d', rb'\x4c\x8d\x05', rb'\x4c\x8b\x05', rb'\x4c\x8d\x0d', rb'\x48\x8d\x35', rb'\x48\x8d\x3d', rb'\xf2\x0f\x10\x05', rb'\x8b\x15', rb'\x44\x8b\x05', rb'\x44\x8b\x0d']
        for p in pats:
            for m in re.finditer(b'(?=(' + p + b'(....)))', code, re.S):
                rel = struct.unpack('<i', m.group(2))[0]
                end = m.start() + len(m.group(1))
                cands.append((m.start(), pe.image_base + frva + end + rel, m.group(1)[:len(p)]))
    else:
        pats = [rb'\xa1', rb'\x8b\x0d', rb'\x8b\x15', rb'\x8b\x1d', rb'\x8b\x35', rb'\x8b\x3d', rb'\xb8', rb'\xb9', rb'\xba', rb'\xbb', rb'\xbe', rb'\xbf', rb'\xc7\x45.', rb'\x8b\x04\x85', rb'\x8b\x04\x8d', rb'\x8b\x04\x95', rb'\x8b\x14\x85', rb'\x8b\x0c\x85', rb'\x8b\x04\xc5', rb'\x8b\x14\x8d', rb'\x8b\x14\x95', rb'\x8b\x14\xd5', rb'\x8b\x0c\x8d', rb'\x8b\x0c\x95', rb'\x8b\x0c\xcd', rb'\x3b\x05', rb'\x39\x05', rb'\xff\xb3', rb'\xff\xb0', rb'\xff\xb1', rb'\xff\xb2', rb'\xff\xb6', rb'\xff\xb7', rb'\x8b\x83', rb'\x8b\x80', rb'\x8b\x81', rb'\x8b\x82', rb'\x8b\x86', rb'\x8b\x87', rb'\x8d\x04\x85', rb'\x8d\x04\xc5', rb'\xff\x34\x85', rb'\xff\x34\xc5', rb'\xff\x34\x8d', rb'\xff\x34\xcd', rb'\x8b\x04\xc0', rb'\x8b\x0c\xc5', rb'\x8b\x14\xc5', rb'\x8b\x1c\xc5', rb'\x8b\x34\xc5', rb'\x8b\x3c\xc5', rb'\x05', rb'\x81\xc0', rb'\x81\xc1', rb'\x81\xc2', rb'\x8d\x80', rb'\x8d\x81', rb'\x8d\x82', rb'\x8d\x84.', rb'\x8d\x8c.', rb'\x8d\x94.']
        for p in pats:
            for m in re.finditer(b'(?=(' + p + b'(....)))', code, re.S):
                val = struct.unpack('<I', m.group(2))[0]
                cands.append((m.start(), val, m.group(1)[:len(p)]))
    cands.sort()
    return cands

def plausible_va(pe, va):
    try:
        pe.va2off(va); return True
    except Exception:
        return False

def read_varinfo(pe, va, n):
    out = []
    for i in range(n):
        off = pe.va2off(va + i * 40)
        nameptr = pe.ptr(off)
        if pe.is64:
            typ = pe.i32(off + 8)
            mn, mx, df = off + 16, off + 24, off + 32
        else:
            typ = pe.i32(off + 4)
            mn, mx, df = off + 16, off + 24, off + 32
        name = pe.cstr(pe.va2off(nameptr))
        if typ >= 2:
            lo, hi, de = pe.i32(mn), pe.i32(mx), pe.i32(df)
        else:
            lo, hi, de = pe.f64(mn), pe.f64(mx), pe.f64(df)
        out.append({'name': name, 'type': ['REAL', 'REAL_CYCLIC', 'INTEGER', 'INTEGER_NONZERO'][typ] if 0 <= typ < 4 else ('INTEGER' if typ >= 2 else 'REAL'), 'min': lo, 'max': hi, 'default': de})
    return out

def extract(path):
    pe = PE(pathlib.Path(path).read_bytes())
    ex = pe.exports()
    res = {'arch': 'x64' if pe.is64 else 'x86', 'exports': sorted(ex)}
    if 'PluginVarGetName' not in ex:
        res['error'] = 'not a plugin'; return res
    # name
    name = None
    for _, va, _ in find_global_load(pe, ex['PluginVarGetName']):
        if plausible_va(pe, va):
            try:
                p = pe.ptr(pe.va2off(va))
                if plausible_va(pe, p):
                    s = pe.cstr(pe.va2off(p))
                    if re.fullmatch(r'[A-Za-z0-9_]+', s): name = s; break
            except Exception: pass
            try:
                s = pe.cstr(pe.va2off(va))
                if re.fullmatch(r'[A-Za-z0-9_]+', s) and name is None: name = s; break
            except Exception: pass
    res['name'] = name
    # number of variables
    nvars = None
    for _, va, opc in find_global_load(pe, ex['PluginVarGetNrVariables']):
        if opc[:1] == b'\xb8' or opc[:2] == b'\xc7\x45':
            nvars = va; break
        if plausible_va(pe, va):
            try:
                nvars = pe.i32(pe.va2off(va)); break
            except Exception: pass
    if nvars is None:
        # maybe 'mov eax, imm' (b8) for x86 or x64 'mov eax, imm32' (b8)
        off = pe.rva2off(ex['PluginVarGetNrVariables'])
        m = re.search(rb'\xb8(....)', pe.d[off:off+40], re.S)
        if m: nvars = struct.unpack('<I', m.group(1))[0]
    res['nvars'] = nvars
    # VarInfo
    vars_ = None
    if nvars is not None and 0 <= nvars < 64:
        fn = ex.get('PluginVarGetVariableNameAt') or ex.get('PluginVarResetVariable')
        for _, va, _ in find_global_load(pe, fn):
            if plausible_va(pe, va):
                try:
                    v = read_varinfo(pe, va, nvars)
                    if all(re.fullmatch(r'[A-Za-z0-9_]+', x['name']) for x in v):
                        vars_ = v; break
                except Exception: pass
    res['vars'] = vars_
    return res

if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(p, json.dumps(extract(p), indent=1))
