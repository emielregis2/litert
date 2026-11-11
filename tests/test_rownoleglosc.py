# -*- coding: utf-8 -*-
"""Test rownoleglosci (Windows, macOS, Linux; nie wymaga korpusu Wymina - buduje dane syntetyczne):
  1. samotest rownolegle.py,
  2. czkawka_przeglad.py: 1 proces vs 4 procesy (CSV, wydruk, pliki po --napraw),
  3. poprawki_wstecz.py: 1 proces vs 4 procesy (pliki, kopia zip, drugi przebieg).
Uzycie: python tests/test_rownoleglosc.py"""
import os, re, sys, time, random, shutil, subprocess, hashlib, tempfile, zipfile
sys.stdout.reconfigure(errors="replace")
SK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "litert-rozdziel", "scripts")
def run(skrypt, *args):
    t = time.perf_counter(); r = subprocess.run([sys.executable, "-W", "ignore", os.path.join(SK, skrypt)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return time.perf_counter() - t, r.returncode, r.stdout, r.stderr
def h(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
bl = 0
def ocena(nazwa, ok, szczegol=""):
    global bl
    bl += (not ok); print("  %s %s %s" % ("OK  " if ok else "BLAD", nazwa, szczegol))
print("=== 1. samotest rownolegle.py")
dt, rc, out, err = run("rownolegle.py", "--samotest"); print("   " + out.strip().replace("\n", "\n   ")); ocena("samotest", rc == 0 and "SAMOTEST: OK" in out)
# --- dane syntetyczne ---
EN = "the a she he they walked looked took said went saw heard felt knew wanted opened closed smiled laughed turned stood sat house door window table water light morning night hand eyes voice".split()
PL = ["slowo" + chr(97 + i % 26) + chr(97 + i // 26) for i in range(len(EN))]          # tokeny z samych liter, tyle samo co angielskich
cap = lambda s: s[:1].upper() + s[1:]                                   # tylko pierwsza litera (capitalize() zmniejszalby reszte zdania)
random.seed(7); tmp = tempfile.mkdtemp(prefix="rown_syn_"); kat = os.path.join(tmp, "Syn_4"); org = os.path.join(kat, "org"); os.makedirs(org)
wstrz = 0
for i in range(14):
    L_en, L_pl = [], []
    for j in range(260):
        n = random.randint(5, 14); idx = [random.randrange(len(EN)) for _ in range(n)]
        for k in range(1, n):
            while idx[k] == idx[k - 1]: idx[k] = random.randrange(len(EN))
        en = cap(" ".join(EN[x] for x in idx)) + "."; pl = [PL[x] for x in idx]
        if j % 17 == 0: pl.insert(2, "na na"); wstrz += 1                 # zwykle podwojenie (autopoprawka)
        if j % 29 == 0: pl.insert(3, "nasienie nasienie"); wstrz += 1
        if j % 31 == 0: pl.insert(1, "zrumieniła się")                    # blad slownika
        if j % 37 == 0: pl.insert(2, "Sam sam")                           # wyjatek: bez zmian
        L_en.append(en); L_pl.append(cap(" ".join(pl)) + ".")
        if j % 5 == 4: L_en.append(""); L_pl.append("")
    nazwa = "Autor Opowiadanie %02d" % i
    open(os.path.join(org, nazwa + ".txt"), "w", encoding="utf-8", newline="\n").write("\n".join(L_en) + "\n")
    open(os.path.join(kat, nazwa + " pl.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(L_pl) + "\n")
print("\n=== 2. czkawka_przeglad.py (14 plikow syntetycznych, wstrzyknietych autopoprawek: %d)" % wstrz)
res = {}
for pr in (1, 4):
    csv = os.path.join(tmp, "c%d.csv" % pr); dt, rc, out, err = run("czkawka_przeglad.py", kat, "--csv", csv, "--procesy", str(pr)); res[pr] = (dt, rc, out, csv)
ocena("CSV identyczny (1 vs 4 procesy)", h(res[1][3]) == h(res[4][3]), "| czas %.1f s vs %.1f s" % (res[1][0], res[4][0]))
f1 = [l for l in res[1][2].split("\n") if not l.startswith("CSV:")]; f4 = [l for l in res[4][2].split("\n") if not l.startswith("CSV:")]
ocena("wydruk identyczny", f1 == f4); ocena("kody wyjscia 0", res[1][1] == 0 and res[4][1] == 0)
kopie = {}
for pr in (1, 4):
    kk = os.path.join(tmp, "napr%d" % pr); shutil.copytree(kat, kk); zipp = os.path.join(tmp, "napr%d.zip" % pr)
    dt, rc, out, err = run("czkawka_przeglad.py", kk, "--napraw", "--kopia", zipp, "--procesy", str(pr)); kopie[pr] = (kk, zipp, rc, out)
pliki = sorted(f for f in os.listdir(kat) if f.endswith(" pl.txt"))
ocena("pliki po --napraw identyczne (1 vs 4)", all(h(os.path.join(kopie[1][0], f)) == h(os.path.join(kopie[4][0], f)) for f in pliki))
tek = "\n".join(open(os.path.join(kopie[4][0], f), encoding="utf-8").read() for f in pliki)
ocena("zwykle podwojenia usuniete", " na na " not in tek and "nasienie nasienie" not in tek, "| 'Sam sam' zostaje: %s" % ("Sam sam" in tek))
with zipfile.ZipFile(kopie[4][1]) as z: ocena("kopia zip zawiera oryginalne wersje", all(z.read("%s/%s" % (os.path.basename(kopie[4][0]), f)) == open(os.path.join(kat, f), "rb").read() for f in z.namelist() for f in [f.split("/", 1)[1]]))
print("\n=== 3. poprawki_wstecz.py (te same pliki: bledy slownika 'zrumieniła się')")
wy = {}
for pr in (1, 4):
    rk = os.path.join(tmp, "w%d" % pr); shutil.copytree(kat, os.path.join(rk, "Syn_4")); zipp = os.path.join(tmp, "w%d.zip" % pr)
    dt, rc, out, err = run("poprawki_wstecz.py", "--korzen", rk, "--procesy", str(pr), "--kopia", zipp); dt2, rc2, out2, _ = run("poprawki_wstecz.py", "--korzen", rk, "--sucho", "--procesy", str(pr)); wy[pr] = (rk, rc, out, out2, dt)
zam = re.search(r"zamian: (\d+)", wy[1][2])
ocena("kody wyjscia 0", wy[1][1] == 0 and wy[4][1] == 0, "| zamian: %s" % (zam.group(1) if zam else "?"))
ocena("pliki identyczne (1 vs 4 procesy)", all(h(os.path.join(wy[1][0], "Syn_4", f)) == h(os.path.join(wy[4][0], "Syn_4", f)) for f in pliki))
ocena("bledy slownika poprawione, drugi przebieg 0 zmian", "zrumieniła się" not in "".join(open(os.path.join(wy[4][0], "Syn_4", f), encoding="utf-8").read() for f in pliki) and "plikow do zmiany: 0" in wy[4][3])
shutil.rmtree(tmp, ignore_errors=True)
print("\nWYNIK TESTU ROWNOLEGLOSCI: %s" % ("OK" if bl == 0 else "%d BLEDOW" % bl)); sys.exit(0 if bl == 0 else 1)
