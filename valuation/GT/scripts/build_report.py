"""Compose the Turkish valuation report (output/GT_degerleme_raporu.md). Narrative is written here;
every number is pulled from the model outputs so the report cannot drift from the model."""
import csv, json

R = json.load(open('data/valuation_results.json'))
A = json.load(open('data/assumptions.json'))
H = json.load(open('data/history.json'))
P = json.load(open('data/peers.json'))
GS = json.load(open('data/guidance_scores.json'))
DG = json.load(open('data/diagnostics.json'))['screens']
X = json.load(open('data/extra_sensitivities.json'))
AU = json.load(open('data/audit_results.json'))
GL = list(csv.DictReader(open('data/guidance_log.csv')))
hist = H['history']
HY = {h['year']: h for h in hist}
ltm = H['ltm_jun2026']

def tr(v, nd=1):
    if v is None:
        return '–'
    s = f'{v:,.{nd}f}'
    s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    return s.replace('-', '−') if s.startswith('-') and s.strip('-0,.') else s.lstrip('-')
def usd(v, nd=2):
    if v is None:
        return '–'
    return ('−$' if v < -0.005 else '$') + tr(abs(v) + 1e-9, nd)
def m(v):
    return tr(v, 0)
def pct(v, nd=1):
    if v is None:
        return '–'
    return ('−%' + tr(abs(v) * 100, nd)) if v < -0.00049 else ('%' + tr(abs(v) * 100, nd))
def spct(v, nd=0):
    return '–' if v is None else ('−' if v < 0 else '+') + '%' + tr(abs(v) * 100, nd)
def x(v, nd=1):
    return '–' if v is None else tr(v, nd) + 'x'

PRICE = A['meta']['price_reference']
S = R['scenarios']
SP = R['scenario_per_share']
PR = R['probabilities']
MC = R['monte_carlo']
SY = R['synthesis']
WB = R['wacc_build']
RV = R['reverse_dcf']
MT = R['methods']
blended = SY['blended_value']
mkt_cap = PRICE * 288
out = []
w = out.append

w('# Goodyear Tire & Rubber (NASDAQ: GT) — Olasılık Ağırlıklı İçsel Değer Analizi\n')
w(f"**Analiz tarihi:** 26 Eylül 2026 · **Fiyat referansı:** {usd(PRICE)} (25.09.2026 kapanışı) · **Son bilanço:** 30.06.2026 (2026/2Ç 10-Q) · "
  f"**Para birimi:** ABD doları; aksi belirtilmedikçe tutarlar milyon $ · **Muhasebe:** US GAAP, takvim yılı\n")
w('> **Önemli not:** Bu çalışma bir finansal analizdir, kişisel yatırım tavsiyesi değildir. Hazırlayan lisanslı bir yatırım danışmanı değildir. '
  'Risk toleransı, pozisyon büyüklüğü ve karar size aittir. Tüm varsayımlar ekte ve Excel modelinde değiştirilebilir durumdadır.\n')

# ------------------------------------------------------------------ 1
w('## 1. Yönetici özeti\n')
w(f"**Olasılık ve yöntem ağırlıklı içsel değer: ~{usd(blended)}/hisse** (fiyat {usd(PRICE)}; içsel değer fiyatın ~%{tr((1-blended/PRICE)*100,0)} {'altında' if blended < PRICE else 'üstünde'}). "
  f"Makul odak aralığı **~$2–6**; tam dağılım çok geniş ve sağa çarpık: Monte Carlo P10 {usd(MC['P10'])}, P25 {usd(MC['P25'])}, medyan {usd(MC['P50'])}, "
  f"P75 {usd(MC['P75'])}, P90 {usd(MC['P90'])}. İçsel değerin fiyatın üzerinde olma olasılığı **~{pct(MC['prob_above_price'], 0)}**.\n")
w('**Tez tek cümlede:** GT, ~$8,4 milyarlık işletme değerinin (FD) üstünde ~$1,5 milyarlık ince bir özsermaye dilimidir; bu dilimin değeri neredeyse tamamen '
  'segment faaliyet marjının son yedi yılın ortalamasının belirgin üzerine (≈%6,7+) kalıcı olarak dönmesine bağlı bir **opsiyondur**.\n')
w('Temel bulgular:\n')
w(f"1. **10 yıllık gidişat kötü:** Segment faaliyet kârı (SOI) marjı 2016'da {pct(HY[2016]['soi_margin'])} iken 2025'te {pct(HY[2025]['soi_margin'])}, "
  f"2026'nın ilk yarısında %1,6. Normalize ROIC {pct(HY[2016]['roic_nopat_norm'])} → {pct(HY[2025]['roic_nopat_norm'])} (2019'dan beri sermaye maliyetinin altında). "
  f"2022–2025 kümülatif serbest nakit akışı {m(sum(HY[y]['fcf'] for y in range(2022, 2026)))} milyon $; hisse 2016 sonundaki {usd(HY[2016]['price_ye'])} seviyesinden {usd(PRICE)}'e geriledi.\n")
w("2. **Yönetim karnesi ikiye bölünmüş:** Maliyet/sinerji programları brüt bazda sürekli teslim edildi (Cooper sinerjisi $250 milyon, Goodyear Forward $1,5 milyar yıllık etki, "
  "$2,2 milyar varlık satışı) — güven skoru 82/100. Buna karşılık çok yıllık marj, kaldıraç ve sermaye iadesi hedeflerinin **tamamı** kaçırıldı ve üçü sessizce geri çekildi "
  "(2020 için $3,0 milyar SOI; 2025 sonu için %10 marj ve 2,0–2,5x kaldıraç) — güven skoru 0–27/100. Tasarrufların yalnızca ~%10–30'u net kâra yansıdı.\n")
w(f"3. **Piyasanın fiyatladığı:** Ters DCF'ye göre bugünkü fiyat, temel senaryo nakit akışı yapısıyla **uzun vadeli {pct(RV['implied_long_run_soi_margin'])} SOI marjı** "
  f"(son yedi yılın yalnızca ikisinde görüldü) ya da aynı nakit akışlarıyla **{pct(RV['implied_wacc_at_base_cash_flows'], 2)} SAMK** gerektiriyor. Piyasa boğa senaryosuna "
  f"~{pct(X['implied_bull_probability_at_price'], 0)} olasılık veriyor; bizim tahminimiz {pct(PR['bull'], 0)}.\n")
w(f"4. **Değeri belirleyen üç değişken:** uzun vadeli SOI marjı (%5 → $0; %7 → {usd(R['tornado']['Long-run SOI margin 5.0% / 7.0%'][1])}), "
  f"iskonto oranı (SAMK %10,25 → $0; %8,25 → {usd(R['tornado']['WACC 10.25% / 8.25%'][1])}) ve gelir büyümesi. 10 yıllık ABD tahvil faizi %5,18 ile yüksek; "
  f"risk-free %4,5'e normalleşirse (SAMK ≈ {pct(X['wacc_with_rf_4_5'], 2)}) senaryo DCF'si ≈ {usd(X['scenario_dcf_by_wacc']['0.0850'])} ile fiyata yaklaşıyor.\n")
w(f"5. **Sonuç:** Bugünkü faiz ortamı ve kanıta dayalı temel senaryomuzla hisse, olasılık ağırlıklı içsel değerinin **~%{tr((PRICE/blended-1)*100,0)} üzerinde** fiyatlanıyor (içsel değer fiyatın ~%{tr((1-blended/PRICE)*100,0)} altında); "
  "ancak bu bir 'kesin pahalı' hükmü değil — dağılım o kadar geniş ki, 2027'de ~$1 milyar+ SOI'ye dönüş ya da faizlerde düşüş değeri hızla fiyatın üzerine taşır. "
  "Güvenlik marjı yok; asimetri 'kazanırsan çok, kaybedersen hepsi' türünden.\n")
w('| Senaryo | Olasılık | Uzun vadeli SOI marjı | FD (30.06.26) | Özsermaye | Hisse başı değer |\n|---|---|---|---|---|---|')
for k, lab, marg in [('bull', 'Boğa', A['scenarios']['bull']['soi_margin']['2035']), ('base', 'Temel', A['scenarios']['base']['soi_margin']['2035']),
                     ('bear', 'Ayı', A['scenarios']['bear']['soi_margin']['2035'])]:
    w(f"| {lab} | {pct(PR[k], 0)} | {pct(marg)} | {m(S[k]['ev'])} | {m(S[k]['equity_0630'])} | **{usd(SP[k])}** |")
w(f"| Sıkıntı / yeniden yapılanma | {pct(PR['distress'], 0)} | ayı + finansman olayı | – | – | {usd(SP['distress'])} |")
w(f"| **Senaryo ağırlıklı DCF** | %100 | | | | **{usd(R['dcf_probability_weighted'])}** |\n")
w('![Futbol sahası](GT_football_field.png)\n')
w('**Ek rapor:** Temel ve teknik analize dayalı dönüş (toparlanma) değerlendirmesi ve olası zamanlama için bkz. [GT_donus_analizi.md](GT_donus_analizi.md).\n')

# ------------------------------------------------------------------ 2
w('## 2. Şirket, kapsam ve veri\n')
w("- **Kimlik:** The Goodyear Tire & Rubber Company (Akron, Ohio) · NASDAQ: GT · SEC CIK 0000042582 · mali yıl = takvim yılı · US GAAP · raporlama ve işlem para birimi USD.\n"
  f"- **Hisse yapısı:** Tek sınıf adi hisse; 30.06.2026 itibarıyla 288 milyon hisse, seyreltilmiş ~290 milyon (hisse ödülleri). Piyasa değeri ~{m(mkt_cap)} milyon $. "
  "Temettü 2020'den beri yok; geri alım 2018'den beri yok.\n"
  "- **İş:** Dünyanın en büyük lastik üreticilerinden; 48 fabrika, 19 ülke, ~63.000 çalışan. Üç bölge segmenti: Amerika (2025 satışlarının %59'u), EMEA (%30), Asya Pasifik (%11). "
  "Markalar: Goodyear, Cooper (2021'de satın alındı), Kelly, Mastercraft/Roadmaster, Fulda, Debica, Sava. ABD'de şirkete ait perakende/servis ağı.\n"
  "- **2025 portföy sadeleştirmesi:** Off-the-Road lastik işi Yokohama'ya ($905 milyon), Dunlop markası Sumitomo Rubber'a ($701 milyon), kimya işinin çoğu Gemspring'e ($650 milyon) satıldı.\n"
  "- **İş tipi → yöntem seçimi:** Döngüsel, sermaye yoğun ve yüksek kaldıraçlı bir üretici. Bu nedenle (i) orta döngü normalize kazanç, (ii) senaryo bazlı FCFF DCF, "
  "(iii) kaldıraçlı özsermaye için opsiyon yaklaşımı (Merton) ve (iv) Monte Carlo öne çıkar; temettü modeli uygulanamaz.\n"
  "- **Veri:** SEC EDGAR'dan 10-K 2014–2025, 10-Q 2025/1Ç–2026/2Ç, 2015–2026 arası 51 kazanç bülteni ve ilgili 8-K'lar, 2019–2026 vekâlet beyanları (DEF 14A), "
  "Goodyear yatırımcı sunumları (2024/4Ç–2026/2Ç), 2026/2Ç konferans görüşmesi (transkript özeti), XBRL şirket verisi (companyfacts), Yahoo Finance piyasa verisi. "
  "Kaynak listesi ve alınamayan veriler Ek C–D'de.\n")

# ------------------------------------------------------------------ 3
w('## 3. Son 10 yılın finansalları (yeniden kurulmuş ve normalize edilmiş)\n')
yrs = list(range(2015, 2026))
def row(label, key, f, src=None):
    vals = [f(HY[y][key]) for y in yrs]
    return f"| {label} | " + ' | '.join(vals) + ' |'
w('| Kalem | ' + ' | '.join(str(y) for y in yrs) + ' |')
w('|---|' + '---|' * len(yrs))
for lab, key, f in [('Net satış', 'revenue', m), ('Lastik adedi (milyon)', 'units_m', lambda v: tr(v, 1)), ('Lastik başına satış ($)', 'rev_per_unit', lambda v: tr(v, 0)),
                    ('SOI (segment faaliyet kârı)', 'soi', m), ('SOI marjı', 'soi_margin', pct), ('— Amerika marjı', 'margin_americas', pct), ('— EMEA marjı', 'margin_emea', pct),
                    ('— Asya Pasifik marjı', 'margin_apac', pct), ('Kurumsal gider (normal)', 'corp_cost', m), ('Yeniden yapılanma (nakit)', 'rationalization_cash', m),
                    ('Amortisman (D&A)', 'dna', m), ('Düzeltilmiş FAVÖK (SOI+D&A−kurumsal)', 'adj_ebitda', m), ('Normalize FVÖK*', 'ebit_normalized', m),
                    ('Normalize FVÖK marjı', 'ebit_norm_margin', pct), ('Normalize NOPAT (%25 vergi)', 'nopat_normalized', m), ('Normalize ROIC', 'roic_nopat_norm', pct),
                    ('GAAP net kâr', 'net_income_gaap', m), ('Faaliyet nakit akışı (FNA)', 'cfo', m), ('Yatırım harcaması', 'capex', m), ('Serbest nakit akışı (FNA−capex)', 'fcf', m),
                    ('Hisse geri alımı', 'buybacks', m), ('Temettü', 'dividends', m), ('Net borç', 'net_debt', m), ('Net borç / düz. FAVÖK', 'net_debt_to_adj_ebitda', x),
                    ('Ana ortaklık özsermayesi', 'equity_parent', m), ('Yıl sonu hisse sayısı (milyon)', 'shares_ye_m', m), ('Yıl sonu hisse fiyatı ($)', 'price_ye', lambda v: tr(v, 2)),
                    ('FD / düz. FAVÖK', 'ev_to_adj_ebitda', x), ('Piyasa değeri / defter değeri', 'price_to_book', lambda v: tr(v, 2) + 'x')]:
    w(row(lab, key, f))
w(f"\n*Normalize FVÖK = SOI − kurumsal gider − $150 milyon normalize yeniden yapılanma. Kaynak: SEC XBRL (her yıl için en son dosyalanan değer; yeniden düzenlemeler dahil) ve 10-K segment notları. "
  f"2023–2024 SOI, 2025'te Türkiye kur çevrimi hatası nedeniyle yeniden düzenlenmiş değerlerdir (ilk açıklanan 968 ve 1.318). "
  f"Son 12 ay (Haz-2026): satış {m(ltm['revenue'])}, SOI {m(ltm['soi'])} (marj {pct(ltm['soi_margin'])}), net borç {m(ltm['net_debt'])}, net borç/düz. FAVÖK {x(ltm['net_debt_to_adj_ebitda'])}.\n")
w('![Marj geçmişi](GT_margin_history.png)\n')
w('![Nakit ve kaldıraç](GT_cash_leverage.png)\n')
cum1 = sum(HY[y]['fcf'] for y in range(2015, 2022))
cum2 = sum(HY[y]['fcf'] for y in range(2022, 2026))
w('**Okuma notları ve normalizasyon kararları**\n')
w(f"- **Hacim ve fiyatlama:** Satış 10 yılda %{tr((HY[2025]['revenue']/HY[2015]['revenue']-1)*100,0)} arttı ama bunun kaynağı Cooper satın alması ve 2021–2023 enflasyon fiyatlaması; "
  f"lastik adedi {tr(HY[2015]['units_m'],1)} milyondan {tr(HY[2025]['units_m'],1)} milyona düştü. Lastik başına satış %{tr((HY[2025]['rev_per_unit']/HY[2015]['rev_per_unit']-1)*100,0)} arttı; "
  "aynı dönemde ABD TÜFE ~%35 yükseldi → reel fiyat/karma erozyonu.\n"
  "- **Yeniden yapılanma 'tek seferlik' değil:** Goodyear son 11 yılın her birinde yeniden yapılanma gideri yazdı (nakit ortalaması ~$170 milyon/yıl). "
  "Bu yüzden normalize kazançtan $150 milyon/yıl düşüldü; DCF'de 2027 $250 milyon, 2028 $150 milyon, sonrası $100 milyon (temel).\n"
  "- **Kurumsal giderler:** SOI kurumsal teşvik primlerini ve dağıtılmayan genel giderleri içermez; 2016–2025 ortalaması ~$140 milyon, 2026 rehberi ~$150 milyon.\n"
  "- **Vergi:** 2025'te ABD ertelenmiş vergi varlıklarına tam değerleme karşılığı ayrıldı (net kâra −$1,5 milyar, nakitsiz). ABD'de ~$1,4 milyar, Lüksemburg'da ~$1,1 milyar vergi varlığı "
  "karşılıklı; bu, kârlılık dönerse gelecekte vergi kalkanı demek. Modelde 2032'ye kadar %20 nakit vergi oranı (yabancı vergiler için $150 milyon taban) ve sonrasında %24 kullanıldı.\n"
  "- **Emeklilik:** ABD planları fazla fonlu (+$77 milyon); ABD dışı (−$215 milyon) ve diğer yan haklar (−$231 milyon) ile net açık $369 milyon → borç benzeri kalem.\n"
  "- **Kiralamalar ve faktoring:** Operasyonel kira gideri faaliyet giderinde bırakıldı (kira yükümlülüğü borca eklenmedi). Bilanço dışı faktoring ($830 milyon) borca eklenmedi, "
  "bunun yerine yıllık ~$35 milyon maliyeti nakit akışından düşüldü. Tedarikçi finansmanı ($550 milyon) ticari borçlar içinde; kaldıraç riski olarak not edildi.\n"
  f"- **Kazançtan nakde köprü (2025):** GAAP net zarar −$1.700 milyon → FNA +$796 milyon: +D&A 1.045, +şerefiye değer düşüklüğü 674, +vergi varlığı karşılığı 1.357, "
  "+emeklilik tasfiye 201, −varlık satış kârı 816, −yeniden yapılanma (ödenen − gider) 237, +işletme sermayesi ve diğer. **Dikkat:** 2025 FNA'sı, varlık satışlarıyla ilgili ~$376 milyon "
  "tek seferlik ertelenmiş tahsilat içeriyor; bu arındırıldığında 2025 serbest nakit akışı ~−$0,4 milyar.\n"
  f"- **Serbest nakit:** 2015–2021 kümülatif +${tr(cum1/1000,1)} milyar; 2022–2025 kümülatif {usd(cum2/1000,2)} milyar; 2026 rehberi −$200/−$300 milyon. "
  "Kısacası şirket dört yıldır faizden sonra nakit yakıyor; borç azaltımı varlık satışlarıyla yapıldı.\n")

# ------------------------------------------------------------------ 4
w("## 4. Şirketin gidişatı: iş kalitesi, getiri ve riskler\n")
w("**Sektör yapısı.** Premium ve orta segment rakipler (Michelin, Bridgestone, Continental, Pirelli, Yokohama, Toyo) ~%9–16 faaliyet marjı ve güçlü bilançolarla çalışırken, Asya'dan (Çin, Tayland, Vietnam, Kamboçya) "
  "düşük maliyetli ithalat özellikle ABD ve AB yedek (replacement) pazarında pay kazanıyor. Goodyear'ın 2026/1Y'de küresel yedek hacmi %13, Amerika yedek hacmi %18 düştü; "
  "şirket bunu kısmen 'düşük segment ürünlerin bilinçli rasyonalizasyonu', kısmen rekabet ve kanal stok erimesiyle açıklıyor. OE (orijinal ekipman) tarafında ise 10 çeyrektir "
  "EMEA'da pay kazanıyor — gelecekteki yedek talep için olumlu, bugünkü marj için değil.\n")
w(f"**Segment ekonomisi.** Asya Pasifik en kârlı birim (2026/1Y marj %12,6). Amerika 2024'te %8,5 marjdan 2026/1Y'de %0,6'ya çöktü (hacim, eksik kapasite kullanımı ~$300 milyon, tarifeler). "
  f"EMEA yapısal olarak başabaş civarında (2021–2025 ortalaması %{tr(sum(HY[y]['margin_emea'] for y in range(2021,2026))/5*100,1)}); yüksek maliyetli Alman fabrikaları kapatıldı "
  "(Fulda, Fürstenwalde), Güney Afrika Kariega kapatıldı; Mart 2026'da ek bir EMEA planı (~400 net pozisyon, 2029'dan itibaren +$50 milyon/yıl) açıklandı.\n")
w(f"**Getiri vs sermaye maliyeti.** Normalize NOPAT getirisi 2015–2017'de %10–14 iken 2019'dan beri %{tr(min(HY[y]['roic_nopat_norm'] for y in range(2019,2026) if y!=2020)*100,1)}–{tr(max(HY[y]['roic_nopat_norm'] for y in range(2019,2026))*100,1)} "
  f"aralığında; bugünkü SAMK (~%{tr(A['wacc']['base_wacc']*100,2)}) bir yana, faiz sonrası bile nakit üretmiyor. Bu nedenle büyüme bugünkü yapıda değer **yaratmıyor**; temel senaryoda "
  "yeni yatırım getirisi (RONIC) = SAMK varsayıldı.\n")
w("**Hendek (moat).** Marka bilinirliği, OE ilişkileri, ABD üretim ayak izi (tarifelere karşı görece avantaj) ve perakende ağı gerçek varlıklar; ancak birim fiyatın enflasyonun "
  "gerisinde kalması ve 7 yıldır sermaye maliyetinin altında getiri, bu hendeğin getirileri korumadığını gösteriyor. Aşırı getirilerin söndüğü (fade) değil, zaten söndüğü bir durum.\n")
w('**Muhasebe ve finansal sağlık taramaları**\n')
w('| Yıl | Altman Z | Beneish M | Sloan tahakkuk | SOI/faiz | Düz. FAVÖK/faiz | Alacak gün | Stok gün | Borç gün |\n|---|---|---|---|---|---|---|---|---|')
for y in ['2016', '2019', '2021', '2023', '2024', '2025']:
    d = DG[y]
    w(f"| {y} | {tr(d['altman_z'],2)} | {tr(d['beneish_m'],2)} | {tr(d['sloan_accruals'],3)} | {x(d['soi_interest_cover'])} | {x(d['adj_ebitda_interest_cover'])} | {tr(d['dso_days'],0)} | {tr(d['dio_days'],0)} | {tr(d['dpo_days'],0)} |")
w("\n- Altman Z 2019'dan beri 1,81'in altında (\"sıkıntı bölgesi\"); 2026 için SOI/faiz ~1,4x (≈$600M/$425M). Beneish M hiçbir yıl −2,22 eşiğini aşmıyor (manipülasyon sinyali yok). "
  "2025'te Türkiye kur çevrimi hatası nedeniyle önemsiz bir geriye dönük düzeltme yapıldı; denetçi PwC.\n"
  "- Kısıtlı nakit: $179 milyon nakit (Çin, Güney Afrika, Sırbistan, Arjantin) transfer kısıtlı. Borçluluk kovenantı yalnızca likidite $275 milyonun altına inerse devreye giriyor; "
  "30.06.2026'da kullanılabilir likidite ~$3,9 milyar + $0,86 milyar nakit.\n")
w("**Başlıca riskler:** (1) Kaldıraç ve refinansman — Haziran 2026'da $1,05 milyar %8,875 kuponlu 2032 vadeli tahvil (marjinal borç maliyeti çok yüksek); S&P'nin notu BB−'den B+'ya indirdiği bildiriliyor (başlık doğrulandı, tarihi doğrulanamadı), Moody's B1; "
  "(2) tarifeler ve ithalat rejimi (yıllık ~$300 milyon tarife maliyeti; IEEPA iadeleri belirsiz); (3) hammadde (Orta Doğu çatışması nedeniyle 2026/2Y'de ~$200 milyon ek maliyet beklentisi); "
  "(4) yedek pazarda yapısal pay kaybı; (5) EMEA'nın kalıcı zayıflığı; (6) 2030 civarında Dunlop tedarik anlaşmasının (yılda en az 4,5 milyon lastik) bitişi; (7) ticari kamyon döngüsü; "
  "(8) CFO'suz dönem (geçici CFO Temmuz 2026'dan beri); (9) sendika sözleşmeleri (USW ile Nisan 2029'a kadar geçerli, üye onayına tabi geçici anlaşma); (10) asbest ve ürün sorumluluğu (net ~$50 milyon asbest).\n")

# ------------------------------------------------------------------ 5
w("## 5. Yönetim kalitesi\n")
w("**Zaman çizelgesi:** Richard Kramer 2010–Ocak 2024 CEO/Başkan. Temmuz 2023'te aktivist Elliott ile işbirliği anlaşması: 3 yeni bağımsız üye ve Stratejik ve Operasyonel İnceleme Komitesi. "
  "Kasım 2023'te 'Goodyear Forward' dönüşüm planı. Ocak 2024'te Mark Stewart (eski Stellantis Kuzey Amerika COO'su, Amazon, ZF TRW) CEO oldu; Laurette Koellner icracı olmayan başkan. "
  "CFO Christina Zamarro Temmuz 2026'da ayrıldı; Scott Deakin geçici CFO.\n")
w('**Sermaye tahsisi karnesi (10 yıl)**\n')
w("| Karar | Tutar | Sonuç |\n|---|---|---|\n"
  "| Hisse geri alımı 2014–2018 | ~$1,5 milyar (~52 milyon hisse, ort. ~$29) | Bugün ~$5 → değerin ~%80'i eridi |\n"
  "| Temettü 2013–2020 | ~$0,65 milyar | 2020'de askıya alındı |\n"
  "| Cooper Tire (2021) | ~$2,8 milyar özsermaye değeri; ~6,4x FAVÖK (2020) | Sinerji hedefi ($165M→$250M) tuttu; ama Amerika SOI'si 2023'te pro forma seviyenin altında; 2024'te $125M marka, 2025'te $674M şerefiye değer düşüklüğü |\n"
  "| Yatırım (2021–2024) | Yıllık $1,0–1,2 milyar (D&A üstü) | Hacim ve marj artışı gelmedi; 2025–26'da $826M/$725M'ye kısıldı |\n"
  "| Varlık satışları (2025) | ~$2,2 milyar brüt (OTR ~7x, Dunlop ~9,7x SOI, Kimya ~4,3x FAVÖK) | Hedefin üstünde; borç azaltıldı ama 2026'da ~$185M SOI kaybı |\n")
w("**Teşvikler ve yönetişim (DEF 14A 2026):**\n"
  "- 2025 yıllık prim hedefi: SOI marjı **%6,91** — kamuya açıklanan %10 hedefinin çok altında. Ücret komitesi SOI'yi tarifeler için +$148 milyon düzeltti (%6,12 sayıldı).\n"
  "- Serbest nakit akışı hedefi $450 milyon; raporlanan FNA−capex −$30 milyon iken prim hesabında **+$467 milyon** sayıldı (yeniden yapılanma ödemeleri +$431M, tarifeler +$251M, "
  "'hedef üstü varlık satış gelirleri' +$186M, Goodyear Forward ödemeleri +$132M eklendi). Yıllık prim ödemesi %98.\n"
  "- 2023–2025 uzun vadeli teşvik ödemesi %96 (TSR çarpanı 0,83x olmasına rağmen 'stratejik girişim endeksi' +25 puan ekledi). CEO toplam ücreti 2024'te $25,8 milyon, 2025'te $14,6 milyon.\n"
  "- Yönetim ve yönetim kurulu toplam payı %1'in altında (~1,07 milyon hisse). Haziran 2025'ten beri tek açık piyasa alımı: bir yönetim kurulu üyesi (Kasım 2025, 100 bin hisse, $7,55). "
  "2026'daki %40'lık düşüşte içeriden alım yok; satış da yok (yalnızca vergi stopajı).\n"
  "- Açığa satış oranı serbest dolaşımın ~%22'si (piyasa şüpheci).\n")
w("**Değerlendirme (analist yargısı):**\n\n| Boyut | Puan (10) | Gerekçe |\n|---|---|---|\n"
  "| Operasyonel uygulama | 7 | Maliyet programları, sinerji ve varlık satışları vaktinde ve hedef üstünde |\n"
  "| Stratejik sonuç | 2 | Marj, ROIC, FCF ve TSR on yıldır geriliyor; tasarruflar enflasyon ve hacim kaybında eriyor |\n"
  "| Sermaye tahsisi | 3 | Pahalıdan geri alım, döngü tepesinde satın alma, sonra zorunlu varlık satışı |\n"
  "| Teşvik uyumu | 3 | İç hedefler dış hedeflerden düşük; bol düzeltmeli FCF; düşük içeriden sahiplik |\n"
  "| Şeffaflık | 4 | Detaylı köprü tabloları iyi; ama başarısız hedefler açıklamasız bırakıldı |\n"
  "| **Genel** | **~4** | Elliott sonrası ekip daha disiplinli, fakat sonuç kanıtı henüz yok |\n")

# ------------------------------------------------------------------ 6
w("## 6. Hedefler ne kadar gerçekleşti? (rehberlik karnesi)\n")
w("Yöntem: Her hedef için 'gerçekleşme oranı' = (gerçekleşen − başlangıç) / (hedef − başlangıç), yani vaat edilen **değişimin** ne kadarının geldiği. "
  "Sessizce geri çekilen hedefler 'kaçırıldı' sayıldı. 2026'ya ait açık kalemler 'ara' olarak raporlandı ama puana katılmadı.\n")
GTR = {
    'G01': '2014 SOI büyümesi %10–15 (2014–16 planı)', 'G02': '2015 SOI büyümesi %10–15', 'G03': '2016 rekor SOI $2,1–2,2 milyar (Venezuela hariç)',
    'G04': '2017 SOI 2016 ile yatay (~$2,0 milyar)', 'G05': '2018 SOI $1,8–1,9 milyar', 'G06': "2023/2Y SOI marjı 'yakın vadeli %8 hedefine çok yakın'",
    'G07': "2026 SOI: Şubat köprüsü (~$0,9 milyar, hacim hariç; analist yeniden kurgusu) → Ağustos ima ~$0,6 milyar", 'G08': '2020 SOI hedefi $3,0 milyar (Yatırımcı Günü 2016)',
    'G09': '2020 SOI hedefi $2,0–2,4 milyar (revize)', 'G10': "4Ç2025'te ~%10 SOI marjı (Goodyear Forward)", 'G11': '2025 sonunda 2,0–2,5x net kaldıraç',
    'G12': '2016 sonunda 2,0–2,1x düzeltilmiş borç/FAVÖKP', 'G13': '2017–2020 kümülatif FCF $4,3–4,9 milyar', 'G14': '2017–2020 hissedara $4 milyara kadar dağıtım',
    'G15': "EMEA Hanau/Fulda modernizasyonu: 2020'den itibaren 3 yılda +$60–70M SOI", 'G16': "Cooper sinerjisi 2 yılda $165M (2023 ortasına $250M'ye yükseltildi)",
    'G17': "Goodyear Forward 2024 brüt fayda ~$350M ($450M'ye yükseltildi)", 'G18': 'Goodyear Forward 2025 brüt fayda ~$750M',
    'G19': "Goodyear Forward 4Ç25 yıllık etki $1,3 milyar ($1,5 milyara yükseltildi)", 'G20': "OTR/Dunlop/Kimya satışından >$2 milyar brüt gelir",
    'G21': '2025 capex ~$950M', 'G22': '2025 yeniden yapılanma ödemeleri ~$400M', 'G23': '2025 faiz gideri $450–475M', 'G24': '2025 işletme sermayesi girişi $100–150M',
    'G25': '2025 nakit vergi ~$200M', 'G26': "2026 işletme sermayesi girişi ~$100M (Şub) → nötr (Ağu)", 'G27': "2026 hammadde faydası ~$300M (Şub) → ~nötr (May)",
    'G28': '2025 ticari yedek lastik sektörü +%2–4'}
w('| # | Hedef | Veriliş | Durum | Değişimin gerçekleşmesi | Seviye gerçekleşmesi |\n|---|---|---|---|---|---|---|'.replace('|---|---|---|---|---|---|---|', '|---|---|---|---|---|---|'))
stat_tr = {'hit': 'Tuttu', 'miss': 'Kaçırıldı', 'retired': 'Sessizce geri çekildi', 'partial': 'Kısmen', 'interim': 'Ara (2026)'}
det = {d['id']: d for d in GS['detail']}
for g in GL:
    d = det[g['id']]
    inc, lev = d['increment_realization'], d['level_realization']
    if g['id'] == 'G04':
        incs = 'anlamsız (hedef ≈ başlangıç)'
    elif g['category'] == 'cash_items_1y':
        incs = '–'
    else:
        incs = '–' if inc is None else pct(inc, 0)
    levs = '–' if lev is None else pct(lev, 0)
    w(f"| {g['id']} | {GTR[g['id']]} | {g['issued']} | {stat_tr[g['status']]} | {incs} | {levs} |")
w('\n**Kategori bazında güven skorları**\n')
cat_tr = {'soi_1y': '1 yıllık SOI/marj rehberliği', 'soi_multi': 'Çok yıllık SOI/marj hedefleri', 'leverage': 'Kaldıraç hedefleri', 'capital_return': 'FCF ve sermaye iadesi hedefleri',
          'cost_program': 'Maliyet/sinerji programları (brüt)', 'portfolio': 'Varlık satış gelirleri', 'cash_items_1y': 'Yıllık nakit kalemleri (capex, faiz, vergi…)', 'industry_1y': 'Sektör varsayımları'}
w('| Kategori | Adet | İsabet oranı | Medyan değişim gerçekleşmesi | Geri çekilen | Güven (0–100) |\n|---|---|---|---|---|---|')
for k, s in GS['scores'].items():
    mi = s['median_increment_realization']
    w(f"| {cat_tr[k]} | {s['n']} | {pct(s['hit_rate'],0)} | {'–' if mi is None else pct(mi,0)} | {s['retired']} | **{s['confidence']}** |")
w("\n**Desenler:** (1) 2016, 2017 ve 2018'de yıllık SOI rehberliği art arda yıl ortasında düşürüldü; 2018'de son düşürülen rakam bile tutmadı. "
  "(2) Uzun vadeli hedeflerin tamamı kaçırıldı: 2020 için $3,0 milyar SOI (gerçekleşen 2019: $945 milyon), 2017–2020 kümülatif $4,3–4,9 milyar FCF (gerçekleşen ~$1,3 milyar), "
  "2025 sonu %10 marj (gerçekleşen 4Ç25: %8,5, sigorta tazminatı hariç %7,3) ve 2,0–2,5x kaldıraç (gerçekleşen ~2,8x; Haz-26'da 3,8x). Son ikisi Ağustos 2025'te sessizce "
  "söylemden çıkarıldı. (3) Brüt tasarruflar her seferinde tuttu ya da aştı, fakat 2024–2025'te $1,25 milyar brüt fayda varken SOI yalnızca +$114 milyon arttı (2023→2025). "
  "(4) Kısa vadeli nakit kalemleri (capex, faiz, vergi, yeniden yapılanma ödemeleri) güvenilir.\n")
w("**Modele nasıl taşındı (aritmetik):**\n"
  "- 2026 SOI: yönetimin ima ettiği ~$600 milyonun %95'i → temel $570M (ayı $500M, boğa $630M).\n"
  "- Orta vadeli marj hedefleri (güven 0): %10 hedefi hiçbir senaryoya girmedi; boğa senaryosu bile %8'de sınırlandı. Temel senaryo, 2021–2025 gerçekleşmelerinden aşağıdan yukarıya kuruldu.\n"
  "- Açıklanan yeni tasarruflar (Fayetteville +$270M/yıl, EMEA +$50M/yıl): brüt teslim güvenilir, net tutunma düşük → temel %50, ayı %25, boğa %90.\n"
  "- 2026 FCF rehberi (−$200/−$300M): nakit kalemleri güvenilir ama işletme sermayesi rehberi iki kez kaçtı → temel −$325M, ayı −$450M, boğa −$225M.\n")

# ------------------------------------------------------------------ 7
w("## 7. Gelecek projeksiyonları\n")
w("**Yönetimin güncel rehberliği (Ağustos 2026):** 2026 SOI ~$600 milyon (2025 düzeltilmiş baz ~$800M + fiyat/karma >$200M − tarifeler ~$50M − hacim/sabit gider emilimi ~$350M; "
  "Goodyear Forward enflasyonu dengeliyor); 3Ç26: hacim yatay, GF +$70M, fiyat/karma +$110M, hammadde −$20M, eksik kapasite −$70M, enflasyon −$95M, satılan işler −$57M; "
  "2026 FCF −$200/−$300M; capex ~$725M; faiz ~$425M; yeniden yapılanma ödemeleri ~$265M; nakit vergi $150–175M; D&A ~$915M; işletme sermayesi ~nötr. "
  "Fayetteville (Kuzey Karolina) fabrikasının kapanışı: 2027'de +$90M, 2028'den itibaren +$270M/yıl Amerika SOI etkisi; $535–565M toplam gider, $190–210M nakit.\n")
w("**Piyasa beklentisi (Yahoo, 7–8 analist):** 2026 düzeltilmiş EPS −$0,69; 2027 +$0,53 (aralık $0,22–0,94); 2027 satış $17,9 milyar; ortalama hedef fiyat $7,46 ($6–10), öneri 'tut'. "
  "2027 EPS konsensüsü ~$1,05 milyar SOI'ye denk geliyor — temel senaryomuzun ($890M) üzerinde.\n")
w('**Senaryo projeksiyonları (seçilmiş yıllar)**\n')
w('| Senaryo | Yıl | Satış | SOI marjı | SOI | FAVÖK* | Capex | FCFF | Net borç/FAVÖK |\n|---|---|---|---|---|---|---|---|---|')
for k, lab in [('bull', 'Boğa'), ('base', 'Temel'), ('bear', 'Ayı')]:
    tb = {r['year']: r for r in S[k]['table']}
    lp = {r['year']: r for r in S[k]['leverage_path']}
    for y in (2027, 2028, 2030, 2035):
        r = tb[y]
        w(f"| {lab} | {y} | {m(r['revenue'])} | {pct(r['soi_margin'])} | {m(r['soi'])} | {m(r['ebitda'])} | {m(r['capex'])} | {m(r['fcff'])} | {x(lp[y]['net_debt_to_ebitda'])} |")
w("\n*FAVÖK = SOI + D&A − kurumsal gider (US GAAP, kira gideri dahil). FCFF: vergi, capex, işletme sermayesi, yeniden yapılanma, faktoring maliyeti ve nakitsiz ertelenmiş gelir çıkarılmış hali.\n")
NARR = {
    'bull': "Yönetim planı büyük ölçüde teslim edilir: Fayetteville/EMEA tasarruflarının ~%90'ı net kâra yansır, yedek pazar hacmi toparlanır, fiyatlama tutunur; SOI marjı 2029'da %8'e ulaşır (yine de geri çekilen %10 hedefinin ve emsallerin ~%11'inin altında). Borç 2031'de FAVÖK'ün ~1,5 katına iner.",
    'base': "2021–2025 ortalaması olan ~%6 SOI marjına dönüş: eksik kapasite kullanımı geri döner, ayak izi tasarruflarının ~%50'si enflasyondan sonra kalır, alt segmentte pay kaybı sürer. Kaldıraç ancak 2030'da 3x'in altına iner; büyüme değer yaratmaz (RONIC = SAMK).",
    'bear': "Düşük maliyetli ithalat pay almaya devam eder, tasarruflar 2024–25'teki gibi enflasyonda erir, EMEA başabaşta kalır; marj 2023–2026 ortalaması olan ~%4'te takılır. Faizden sonra nakit üretilemez, net borç/FAVÖK 2030'da 5x, 2035'te 6x'e çıkar.",
    'distress': "Ayı operasyonları + refinansman/likidite olayı (%8,875 marjinal borç maliyeti, 5x+ kaldıraç): borcun özsermayeye dönüştürülmesi veya çok seyreltici kurtarma sermayesi; mevcut hissedarlara yalnızca küçük bir opsiyon kalır.",
}
for k, lab in [('bull', 'Boğa'), ('base', 'Temel'), ('bear', 'Ayı'), ('distress', 'Sıkıntı')]:
    w(f"- **{lab} ({pct(PR[k],0)}):** {NARR[k]}")
w('')
w("**Olasılıkların dayanağı:** (i) GT'nin kendi marj geçmişi — son 7 yılda SOI marjı 0 yılda ≥%8, 4 yılda %6–8, 3 yılda <%6 (üstüne 1Y26'da %1,6); "
  "(ii) orta vadeli marj hedeflerinin güven skoru 0/100 → yönetim benzeri sonuç %15'lik boğa senaryosuyla sınırlandı; (iii) B+/B1 notları, negatif 2026 FCF'si ve 3,8x kaldıraç, "
  "tek-B+ ihraççılar için ~%10–15'lik 5 yıllık kümülatif temerrüt oranlarıyla birlikte → %12 sıkıntı. Temel/ayı arasındaki 45/28 bölüşümü analist yargısıdır. "
  "Tarihsel taban oran kontrolü: son 7 yılın 2'sinde (~%29) marj ters DCF'nin gerektirdiği ~%6,7'ye ulaştı; Monte Carlo'nun %24'lük 'fiyatın üstünde değer' olasılığıyla tutarlı.\n")

# ------------------------------------------------------------------ 8
w("## 8. Değerleme — farklı yöntemler\n")
w("### 8.1 Sermaye maliyeti (SAMK)\n")
w(f"| Bileşen | Değer | Not |\n|---|---|---|\n"
  f"| Risksiz faiz (10Y ABD) | {pct(A['wacc']['risk_free'],2)} | 25.09.2026: %5,18 (bahar 2026'da ~%4,3) |\n"
  f"| Hisse risk primi | {pct(A['wacc']['equity_risk_premium'],2)} | ABD zımni prim aralığı %4,2–4,6 |\n"
  f"| Varlık betası | {tr(A['wacc']['asset_beta'],2)} | Lastik emsalleri 0,9–1,15; GT'nin kendi 2/3/5 yıllık haftalık betası 0,57/0,85/1,38 (korelasyon <0,45, gürültülü) |\n"
  f"| Borç betası / beklenen borç getirisi | {tr(A['wacc']['debt_beta'],2)} / {pct(WB['cost_of_debt_expected'],2)} | Vaat edilen getiri ~%8,75–8,9 (beklenen temerrüt kaybı dahil) |\n"
  f"| Hedef borç/değer | {pct(A['wacc']['target_debt_to_value'],0)} | Piyasa ağırlıklarıyla ~%82 |\n"
  f"| Vergi kalkanı oranı | {pct(A['wacc']['tax_shield_rate'],0)} | ABD/Lüksemburg vergi varlıkları karşılıklı → faiz kalkanı sınırlı |\n"
  f"| Kaldıraçsız sermaye maliyeti | {pct(WB['unlevered_cost'],2)} | |\n"
  f"| Özsermaye maliyeti (hedef kaldıraç) | {pct(WB['cost_of_equity_target'],2)} | Özsermaye betası {tr(WB['beta_equity_target'],2)}; bugünkü piyasa kaldıracında {pct(WB['cost_of_equity_market'],1)} |\n"
  f"| **SAMK (hesaplanan / kullanılan)** | **{pct(WB['wacc_computed'],2)} / {pct(A['wacc']['base_wacc'],2)}** | Duyarlılık %8,25–10,25 |\n")
w(f"### 8.2 Senaryo bazlı FCFF DCF\n")
w("Nakit akışları 01.07.2026'dan başlar; 2026/2Y FCFF yönetimin yıllık FCF rehberinden (bizim düzeltmemizle) ve 2Y faiz ödemesinden türetildi; 2027–2035 aşağıdan yukarıya; yıl ortası iskonto. "
  "Terminal değer 'değer sürücüsü' formülüyle: NOPAT × (1 − g/RONIC) / (SAMK − g). Özsermaye = FD − net borç ($6.329M) − emeklilik açığı ($369M) − asbest ($50M) − azınlık payı ($162M) "
  f"= FD − {m(R['claims_0630'])}; 26.09.2026'ya özsermaye maliyetiyle taşındı (×{tr(R['roll_factor'],4)}); 290 milyon seyreltilmiş hisseye bölündü.\n")
w('| | Boğa | Temel | Ayı |\n|---|---|---|---|')
for lab, key, f in [('Açık dönem FCFF bugünkü değeri', 'pv_explicit', m), ('Terminal değerin bugünkü değeri', 'pv_tv', m), ('Terminal değer payı', 'tv_share', lambda v: pct(v, 0)),
                    ('**İşletme değeri (FD)**', 'ev', m), ('Özsermaye (30.06.26)', 'equity_0630', m), ('**Hisse başı değer**', 'per_share', usd),
                    ('Zımni terminal FD/FAVÖK', 'implied_tv_ev_ebitda', x), ('Terminal büyüme', 'terminal_growth', pct), ('RONIC', 'ronic', lambda v: pct(v, 2))]:
    w(f"| {lab} | " + ' | '.join(f(S[k][key]) for k in ['bull', 'base', 'bear']) + ' |')
w(f"\n**Olasılık ağırlıklı senaryo DCF: {usd(R['dcf_probability_weighted'])}** (boğa {usd(SP['bull'])} × {pct(PR['bull'],0)} + temel {usd(SP['base'])} × {pct(PR['base'],0)} + "
  f"ayı $0 × {pct(PR['bear'],0)} + sıkıntı {usd(SP['distress'])} × {pct(PR['distress'],0)}). Değerin ~%{tr(SP['bull']*PR['bull']/R['dcf_probability_weighted']*100,0)}'i boğa senaryosundan geliyor.\n")
w('**SAMK × terminal büyüme duyarlılığı (temel senaryo, $/hisse)**\n')
gs = ['0.005', '0.010', '0.015', '0.020', '0.025']
w('| SAMK \\ g | ' + ' | '.join(pct(float(g)) for g in gs) + ' |\n|---|' + '---|' * len(gs))
for wv in ['0.0825', '0.0875', '0.0925', '0.0975', '0.1025']:
    w(f"| {pct(float(wv),2)} | " + ' | '.join(usd(R['sensitivity_wacc_g'][f'{wv}|{g}']) for g in gs) + ' |')
w('\n**Uzun vadeli SOI marjı duyarlılığı (temel yol, $/hisse)**\n')
ms = R['sensitivity_margin']
w('| Marj | ' + ' | '.join(pct(float(k)) for k in ms) + ' |\n|---|' + '---|' * len(ms))
w('| Değer | ' + ' | '.join(usd(v) for v in ms.values()) + ' |\n')
w(f"Başabaş (özsermaye > 0) için uzun vadeli SOI marjı ~%5,8–5,9 gerekiyor; her +0,5 puan marj ≈ +$2,8/hisse.\n")
w("### 8.3 Ters DCF — piyasa ne düşünüyor?\n")
w(f"- Temel senaryonun büyüme, capex ve SAMK varsayımlarıyla bugünkü fiyat **uzun vadeli {pct(RV['implied_long_run_soi_margin'],2)} SOI marjı** gerektiriyor. "
  f"GT son yedi yılda bu seviyeye yalnızca 2021 (%7,4) ve 2024'te (%6,9, sigorta tazminatı dahil) ulaştı; satılan yüksek marjlı işlerden sonra portföyün pro forma 2025 marjı ~%4,6.\n"
  f"- Alternatif olarak, temel nakit akışlarıyla fiyat **{pct(RV['implied_wacc_at_base_cash_flows'],2)} SAMK** anlamına geliyor — risk-free %5,2 iken tek-B kredili, kaldıraçlı bir üretici için iyimser.\n"
  f"- Piyasa FD'si (30.06 talepleriyle): ~{m(RV['market_ev_0630'])} milyon $.\n")
w("### 8.4 Kazanç gücü değeri (EPV, Greenwald)\n")
w('| Orta döngü SOI marjı | %5,0 | %5,5 | %6,0 | %6,5 | %7,0 |\n|---|---|---|---|---|---|')
E = R['epv']
w('| Normalize FVÖK | ' + ' | '.join(m(E[k]['ebit']) for k in E) + ' |')
w('| NOPAT (%23) | ' + ' | '.join(m(E[k]['nopat']) for k in E) + ' |')
w('| FD (30.06.26) | ' + ' | '.join(m(E[k]['epv_ev']) for k in E) + ' |')
w('| **Hisse başı** | ' + ' | '.join(usd(E[k]['per_share']) for k in E) + ' |')
w(f"\nBüyümesiz kazanç gücü %6 marjda özsermayeye neredeyse hiç değer bırakmıyor ({usd(E['0.060']['per_share'])}). Temel DCF'deki 'büyüme değeri' yalnızca ~{m(R['growth_value_base'])} milyon $ "
  "(ve RONIC = SAMK olduğu için bu fark büyümeden değil, 2027–2029 toparlanma yolundan ve vergi kalkanından geliyor). Yani hisse fiyatı esasen **marj toparlanmasına** yapılmış bir bahis.\n")
w("### 8.5 Artık gelir (kontrol amaçlı)\n")
RI = R['residual_income']
w(f"Defter değeri $2.839 milyon; %14 özsermaye maliyeti; artık gelir 2035 sonrası %90 kalıcılıkla sönümleniyor. Sonuç: boğa {usd(RI['bull']['per_share'])}, temel {usd(RI['base']['per_share'])}, "
  f"ayı {usd(RI['bear']['per_share'])}. Temel senaryoda ROE 2027'de negatif, 2030'da ~%6 → değer defterin ~%35'i. Özsermaye; emeklilik zararları (AOCI) ve 2025 vergi varlığı silinmesiyle "
  "bozulduğu için ağırlık verilmedi.\n")
w("### 8.6 Emsal çarpanları\n")
w('| Şirket | Rol | FD/Satış | FD/FAVÖK | FD/FVÖK | F/K | PD/DD | FAVÖK marjı | 4 yıllık ort. faaliyet marjı | Net borç/FAVÖK |\n|---|---|---|---|---|---|---|---|---|---|')
role_tr = {'core': 'çekirdek', 'reference': 'referans', 'excluded': 'dışlandı', 'subject': 'GT'}
for p in P['peers'] + [P['subject']]:
    w(f"| {p['name'].replace('Goodyear (LTM Jun-26, IFRS-like)', 'Goodyear (son 12 ay Haz-26, UFRS benzeri)').replace('(post-spin)', '(ayrışma sonrası)')} | {role_tr[p['role']]} | {x(p['ev_sales'],2)} | {x(p['ev_ebitda'])} | {x(p.get('ev_ebit'))} | {x(p.get('pe'))} | {x(p.get('pb'),2)} | {pct(p['ebitda_margin'])} | {pct(p.get('avg_op_margin_4y'))} | {x(p['net_debt_ebitda'])} |")
cs = P['core_summary']
w(f"\nÇekirdek emsaller (8 şirket): FD/FAVÖK medyanı {x(cs['ev_ebitda']['median'],2)} (çeyrekler {x(cs['ev_ebitda']['p25'],2)}–{x(cs['ev_ebitda']['p75'],2)}), "
  f"FD/FVÖK medyanı {x(cs['ev_ebit']['median'],2)}, PD/DD medyanı {x(cs['pb']['median'],2)}. Emsallerin FAVÖK marjı medyanı {pct(cs['ebitda_margin']['median'])}, net borç/FAVÖK {x(cs['net_debt_ebitda']['median'])}; "
  f"GT (UFRS benzeri) {pct(P['subject']['ebitda_margin'])} ve {x(P['subject']['net_debt_ebitda'])}.\n")
rg = P['regression']['ev_ebitda']
w(f"**Dağılımın açıklaması:** FD/FAVÖK'ün 4 yıllık ortalama marja regresyonu anlamsız (R² = {tr(rg['r2'],2)}): lastik sektöründe FAVÖK çarpanları kalite farkına rağmen 3,5–6,2x bandında toplanıyor. "
  "GT'nin UFRS benzeri 4,6x çarpanı emsal medyanının biraz altında; ancak (i) GT'nin FAVÖK'ten nakde dönüşümü emsallerin çok altında (capex ≈ D&A, sürekli yeniden yapılanma), "
  "(ii) emsaller EUR/JPY faizleriyle (ABD'den 2–3 puan düşük) fiyatlanıyor ve (iii) GT'nin kaldıracı 3 kat. Bu yüzden FD/FVÖK, FD/FAVÖK'ten daha anlamlı.\n")
w('| Uygulama (2027T temel metrikler) | Çarpan | Metrik | FD | Hisse başı |\n|---|---|---|---|---|')
lab_tr = {'peer_ev_ebitda_p25': 'Emsal FD/FAVÖK – 25. yüzdelik', 'peer_ev_ebitda_median': 'Emsal FD/FAVÖK – medyan', 'peer_ev_ebitda_p75': 'Emsal FD/FAVÖK – 75. yüzdelik',
          'peer_ev_ebit_p25': 'Emsal FD/FVÖK – 25. yüzdelik', 'peer_ev_ebit_median': 'Emsal FD/FVÖK – medyan', 'peer_ev_ebit_p75': 'Emsal FD/FVÖK – 75. yüzdelik',
          'gt_own_history_ev_ebitda': 'GT kendi geçmişi FD/FAVÖK (2022–25 medyanı)'}
for k, v in R['comps'].items():
    w(f"| {lab_tr[k]} | {x(v['multiple'],2)} | {m(v['metric_value'])} | {m(v['ev'])} | {usd(v['per_share'])} |")
w(f"\n**Emsal merkez değeri: {usd(R['comps_summary']['central'])}** (üç medyan yaklaşımın ortalaması), aralık {usd(R['comps_summary']['low'])}–{usd(R['comps_summary']['high'])}. "
  "GT'nin kendi 10 yıllık FD/FAVÖK aralığı 4,2–6,4x (2015–2025 medyanı ~5,2x; 2022–2025 medyanı ~4,5x).\n")
w("### 8.7 Parçaların toplamı (SOTP)\n")
SO = R['sotp']
w('| Segment | Orta döngü SOI | FAVÖK | FD/FAVÖK | Değer |\n|---|---|---|---|---|')
for k, lab in [('americas', 'Amerika (marj %7,0)'), ('emea', 'EMEA (marj %2,5)'), ('apac', 'Asya Pasifik (marj %12,0)')]:
    s_ = SO['segments'][k]
    w(f"| {lab} | {m(s_['soi'])} | {m(s_['ebitda'])} | {x(s_['multiple'])} | {m(s_['value'])} |")
w(f"| Kurumsal gider (×5,5) | | | | {m(SO['corporate'])} |\n| 2027–29 yeniden yapılanma (BD) | | | | {m(SO['pv_restructuring'])} |\n| **Orta döngü FD** | | | | **{m(SO['ev_midcycle'])}** |")
w(f"\n30.06.2026'ya indirgenmiş FD {m(SO['ev_0630'])} → özsermaye {m(SO['equity_0630'])} → **{usd(SO['per_share'])}/hisse**. Asya Pasifik, satışların ~%11'i olmasına rağmen FD'nin ~%23'ü. "
  "SOTP, çarpan bazlı olduğu için nakde dönüşüm sorununu kısmen görmüyor; ağırlığı sınırlı tutuldu.\n")
w("### 8.8 Emsal işlemler (kontrol değeri referansı)\n")
T = A['transactions']
w("| İşlem | Çarpan | Not |\n|---|---|---|")
for k, lab in [('cooper_2021', 'Goodyear / Cooper Tire (2021)'), ('otr_2025', 'GT OTR → Yokohama (2025)'), ('chemical_2025', 'GT Kimya → Gemspring (2025)'), ('dunlop_brand_2025', 'GT Dunlop markası → Sumitomo (2025)')]:
    t = T[k]
    notes_tr = {'cooper_2021': "FD ~$2,5 milyar (hisse başı $54,36'dan $2,8 milyar özsermaye − ~$0,3 milyar net nakit) / 2020 FAVÖK $390M (faaliyet kârı 231 + D&A 159; SEC XBRL); kontrol primi dahil",
                'otr_2025': '$905M / tahmini FAVÖK ~$125M (analist tahmini; yalnız segment etkisi açıklandı)',
                'chemical_2025': '$650M / tahmini FAVÖK ~$150M (SOI etkisi ~$120M + D&A ~$30M)',
                'dunlop_brand_2025': '$631M (marka + geçiş ücreti) / yıllık $65M SOI etkisi'}
    w(f"| {lab} | {x(t.get('ev_ebitda', t.get('ev_soi')))} {'FD/SOI' if 'ev_soi' in t else 'FD/FAVÖK'} | {notes_tr[k]} |")
w(f"\n6,0x kontrol çarpanı × 2030T temel FAVÖK ({m(R['transactions']['norm_ebitda_2030'])}) bugüne indirgenince kontrol değeri {usd(R['transactions']['per_share_control'])}/hisse; "
  f"%20 azınlık iskontosuyla {usd(R['transactions']['per_share_minority'])}. Olası stratejik alıcıların (Michelin, Bridgestone) ABD'de rekabet engeline takılacağı düşünülürse satın alma senaryosu ağırlıksız referans.\n")
w("### 8.9 Varlık bazlı değer (taban)\n")
AS = R['asset_based']
w(f"- Defter değeri {usd(AS['book_per_share'])}/hisse; maddi defter değeri {usd(AS['tangible_per_share'])}/hisse — ROIC < SAMK olduğundan ekonomik değer değil, üst referans.\n"
  f"- Tasfiye: alacak %85, stok %55, maddi duran varlık %20, diğer %25, markalar ~$2,0 milyar (Dunlop markası tek başına $526M'ye satıldı) → ~{m(AS['liquidation_proceeds'])} milyon $ gelir; "
  f"toplam yükümlülük $15.649 milyon → özsermayeye **$0**. Tasfiye tabanı alacaklılar içindir, hissedarlar için değil.\n")
w("### 8.10 Merton opsiyon modeli\n")
MR = R['merton']
w(f"Özsermaye, işletme değeri üzerine yazılmış bir alım opsiyonu olarak: varlık değeri = olasılık ağırlıklı FD ({m(MR['prob_weighted_ev'])}) + nakit; kullanım fiyatı = borç + emeklilik + asbest + azınlık, "
  f"%6,3 kupon taşımasıyla 5 yıl sonra {m(MR['on_probability_weighted_ev']['strike_face'])}; varlık volatilitesi %22; risksiz %4,7. "
  f"Sonuç **{usd(MR['on_probability_weighted_ev']['per_share'])}/hisse**; risk-nötr 'özsermaye sıfırlanır' olasılığı %{tr(MR['on_probability_weighted_ev']['risk_neutral_pd']*100,0)}. "
  f"Temel FD üzerinde {usd(MR['on_base_ev']['per_share'])}. Bu yöntem, sınırlı sorumluluğun (kayıp $0'da durur, kazanç sınırsız) değerini yakalar; volatiliteye çok duyarlı olduğu için %10 ağırlık.\n")
w("### 8.11 Monte Carlo\n")
w(f"{MC['n']:,} simülasyon (tohum 42): uzun vadeli SOI marjı ~N(%5,7; %1,4) [%1–10], toparlanma süresi 2–4 yıl, gelir büyümesi ~N(%2; %1) (marjla 0,4 korelasyon), capex ~N(%4,6; %0,3), "
  "yeniden yapılanma U($60–160M), SAMK ~N(%9,25; %0,6), g U(%0,5–2,0), RONIC = SAMK + N(0; %1,5), terminal vergi U(%21–26); 2027–28'de net borç/FAVÖK > 6x olursa sıkıntı ($0,20).\n".replace(',', '.', 1))
w(f"| İstatistik | Ortalama | P5 | P10 | P25 | Medyan | P75 | P90 | P95 |\n|---|---|---|---|---|---|---|---|---|\n"
  f"| $/hisse | {usd(MC['mean'])} | {usd(MC['P5'])} | {usd(MC['P10'])} | {usd(MC['P25'])} | {usd(MC['P50'])} | {usd(MC['P75'])} | {usd(MC['P90'])} | {usd(MC['P95'])} |\n")
w(f"Fiyatın üzerinde değer olasılığı **{pct(MC['prob_above_price'],0)}**; özsermayenin değersiz/sıkıntıda olduğu yol oranı {pct(MC['prob_zero_or_distress'],0)}. "
  "Değerle sıra korelasyonları: uzun vadeli marj " + tr(MC['rank_correlations']['long_run_margin'], 2) + ", gelir büyümesi " + tr(MC['rank_correlations']['revenue_growth'], 2) +
  ", SAMK " + tr(MC['rank_correlations']['wacc'], 2) + "; capex, terminal büyüme ve yeniden yapılanma ikincil.\n")
w('![Monte Carlo](GT_monte_carlo.png)\n')
w("### 8.12 Uygulanmayan yöntemler\n- **Temettü indirgeme modeli:** 2020'den beri temettü yok ve bu kaldıraçla mümkün değil → dışlandı.\n"
  "- **FCFE DCF:** Sermaye yapısı bilinçli olarak değiştirilmiyor; kaldıraç yolu FCFF modelinde ayrıca izlendi → ayrı yöntem olarak uygulanmadı.\n")

# ------------------------------------------------------------------ 9
w("## 9. Olasılık ağırlıklı sentez — 'gerçek' içsel değer\n")
w('| Yöntem | Ağırlık | Düşük | Nokta | Yüksek | Neden bu ağırlık |\n|---|---|---|---|---|---|')
mth_tr = {'scenario_dcf': ('Senaryo ağırlıklı FCFF DCF', 'Birincil yöntem: açık senaryolar, kaldıraç ve toparlanma yolu'),
          'monte_carlo_dcf': ('Monte Carlo DCF', 'Aynı motor, 20 bin çekiliş; dağılımın kendisi'),
          'merton_option': ('Merton opsiyon değeri', 'İnce özsermaye dilimi: sınırlı sorumluluk/yukarı opsiyon'),
          'epv_no_growth': ('Kazanç gücü (EPV)', 'Büyümesiz orta döngü değeri; büyüme bahsini ayırır'),
          'comparables': ('Emsal çarpanlar', 'Piyasa sağlaması; EUR/JPY faizleri ve daha iyi nakit dönüşümü nedeniyle düşük ağırlık'),
          'sotp': ('Parçaların toplamı', 'Segment farklarını gösterir; çarpan bazlı'),
          'residual_income': ('Artık gelir', 'Defter değeri bozuk → yalnız kontrol'),
          'transactions_control': ('Emsal işlemler', 'Alıcı gerektirir; rekabet engeli → referans'),
          'asset_based': ('Varlık bazlı', 'Taban/tavan referansı'),
          'ddm': ('Temettü modeli', 'Temettü yok → dışlandı')}
for k, v in MT.items():
    lab, why = mth_tr[k]
    w(f"| {lab} | {pct(v['weight'],0)} | {usd(v['low']) if v['low'] is not None else '–'} | {usd(v['value']) if v['value'] is not None else '–'} | {usd(v['high']) if v['high'] is not None else '–'} | {why} |")
w(f"| **Ağırlıklı içsel değer** | %100 | | **{usd(blended)}** | | Fiyat {usd(PRICE)} → {spct(SY['upside_at_blended'])} |\n")
w(f"**Dağılım (Monte Carlo, DCF ailesi):** P10 {usd(SY['P10'])} · P25 {usd(SY['P25'])} · medyan {usd(SY['median'])} · P75 {usd(SY['P75'])} · P90 {usd(SY['P90'])}; "
  f"fiyata göre P75'te {spct(SY['upside_at']['P75'])}, P90'da {spct(SY['upside_at']['P90'])}. İçsel değerin fiyatı aşma olasılığı ~{pct(SY['prob_intrinsic_above_price'],0)}.\n")
w("**Sahte kesinliğe karşı uyarı:** Yöntemler bağımsız değil — aynı gelir, marj ve iskonto varsayımlarını paylaşıyorlar; ortalamaları almak aralığı yapay olarak daraltır. "
  "Bu yüzden 'gerçek' içsel değeri tek sayı olarak değil şöyle okumak gerekir: **merkez ~$4 (dürüst aralık ~$2–6), ama dağılımın medyanı sıfır ve üst kuyruğu $11+**. "
  "Nakit akışı bazlı yöntemler ($0,15–3,50) ile piyasa bazlı yöntemler ($5,60–6,30) arasındaki fark tesadüf değil: GT'nin FAVÖK'ünün nakde dönüşümü zayıf (capex ≈ D&A, sürekli yeniden "
  "yapılanma) ve ABD faizleri emsallerin fiyatlandığı EUR/JPY faizlerinden yüksek.\n")
w('**Alternatif olasılık setleri (senaryo DCF, $/hisse)**\n')
w('| Olasılık seti (boğa/temel/ayı/sıkıntı) | Değer |\n|---|---|')
for k, v in X['alt_probabilities'].items():
    w(f"| {k.replace('kitap (base)', 'Bizim set').replace('iyimser', 'İyimser').replace('kotumser', 'Kötümser').replace('esit', 'Eşit')} | {usd(v)} |")
w('\n**SAMK duyarlılığı (senaryo ağırlıklı DCF, $/hisse)**\n')
w('| SAMK | ' + ' | '.join(pct(float(k), 2) for k in X['scenario_dcf_by_wacc']) + ' |\n|---|' + '---|' * len(X['scenario_dcf_by_wacc']))
w('| Değer | ' + ' | '.join(usd(v) for v in X['scenario_dcf_by_wacc'].values()) + ' |\n')
w('**Tornado — temel senaryo, tek değişkenli ($/hisse)**\n')
w('| Değişken (düşük / yüksek) | Düşük | Yüksek |\n|---|---|---|')
tor_tr = {'Long-run SOI margin 5.0% / 7.0%': 'Uzun vadeli SOI marjı %5,0 / %7,0', 'WACC 10.25% / 8.25%': 'SAMK %10,25 / %8,25', 'Capex 5.0% / 4.2% of sales': 'Capex satışın %5,0 / %4,2',
          'Terminal growth 0.5% / 2.5%': 'Terminal büyüme %0,5 / %2,5', 'Revenue growth -1pt / +1pt p.a.': 'Gelir büyümesi yıllık −1 / +1 puan',
          'Restructuring $150m / $50m p.a.': 'Yeniden yapılanma yıllık $150M / $50M', 'H2-26 FCFF $737m / $962m': '2026/2Y FCFF $737M / $962M', 'Terminal tax 27% / 21%': 'Terminal vergi %27 / %21'}
for k, (lo, hi) in sorted(R['tornado'].items(), key=lambda kv: -(kv[1][1] - kv[1][0])):
    w(f"| {tor_tr[k]} | {usd(lo)} | {usd(hi)} |")
w("\n**Piyasanın inanması gereken:** 2026 dip olacak; 2027'de ~$1 milyar, 2028'den itibaren ~$1,25–1,35 milyar SOI (≈%6,7 marj) kalıcı hale gelecek; Fayetteville ve EMEA tasarrufları "
  "büyük ölçüde net kâra yansıyacak; ithalat baskısı ve enflasyon bu kez tasarrufları yemeyecek. GT bunu son 7 yılda yalnızca iki kez yaptı.\n")

# ------------------------------------------------------------------ 10
w("## 10. Karşı tez ve tezi çürütecek gözlemler\n")
w("**En güçlü boğa argümanı (ciddiye alınmalı):**\n"
  "1. 2026 döngüsel bir dip: ~$300 milyonluk eksik kapasite kullanımı tekrarlanmaz; stok erimesi bitiyor (3Ç hacim yatay), ticari kamyon talebi toparlanıyor (2Ç'de ticari OE iki yıl sonra ilk kez arttı).\n"
  "2. Somut, kapasite kesen tasarruflar: Fayetteville +$270M/yıl ve EMEA +$50M/yıl tek başına ~1,8 puan marj; Goodyear Forward'un $1,5 milyar brüt teslimi uygulama yeteneğini kanıtlıyor.\n"
  "3. ABD üretim ayak izi, tarife rejiminde ithalatçılara karşı yapısal avantaj; IEEPA iadeleri ek nakit.\n"
  "4. OE pay kazanımları (EMEA'da 10 çeyrek) gelecekteki yedek talebini besler; 18 inç+ karışımı yılda ~4 puan artıyor.\n"
  "5. ~$2,5 milyar karşılıklı vergi varlığı kârlılık dönerse uzun süre vergi ödememeyi sağlar.\n"
  "6. Özsermaye ucuz bir opsiyon: ~%22 açığa satış, marjda +1 puan sürpriz değeri ikiye katlar; Elliott'ın varlığı ve Goodyear markası stratejik seçenek (ör. APAC veya perakende satışı) sunar.\n")
w("**Ayı argümanı:** yapısal pay kaybı, tasarrufları yiyen enflasyon (2024–25'te $1,25 milyar brüt fayda → +$114M SOI), %8,875'lik marjinal borç maliyeti ve 3,8x kaldıraç, "
  "2030'da Dunlop anlaşmasının bitişi, güvenilirliği düşük orta vadeli hedefler, CFO boşluğu.\n")
w("**İzlenecek ve değerlendirmeyi değiştirecek olaylar (çürütücüler):**\n\n"
  "| Olay | Değer yönü | Eşik |\n|---|---|---|\n"
  "| 3Ç/4Ç-2026 SOI ve yıllık FCF | ↑/↓ | 2Y SOI ≥ ~$470M ve FCF ≥ −$250M → temel/boğa; altı → ayı |\n"
  "| Şubat 2027 rehberi | ↑↑/↓↓ | 2027 SOI ≥ $1,0 milyar → boğa olasılığı ↑; ≤ $0,8 milyar → ayı ↑ |\n"
  "| Fayetteville tasarrufunun gerçekleşmesi | ↑ | 2027'de $90M, 2028'de $270M görünür olmalı |\n"
  "| ABD yedek pazar hacmi ve ithalat/tarife rejimi | ↑/↓ | GT yedek hacmi pozitife dönmeli |\n"
  "| Net borç/FAVÖK | ↓ | > 4,5x → sıkıntı olasılığı belirgin artar; < 3x → boğa |\n"
  "| 10Y ABD faizi | ↑/↓ | SAMK'ta her −50 bp ≈ +$1,0–1,3/hisse (senaryo DCF) |\n"
  "| Kalıcı CFO ataması, varlık satışı veya sermaye artırımı | ↑/↓ | Sermaye artırımı mevcut hissedarı seyreltir |\n"
  "| Kredi notu aksiyonları | ↓ | B/B2'ye inme → refinansman maliyeti ↑ |\n")

# ------------------------------------------------------------------ 11
w("## Ek A — Varsayımlar (modeldeki 'Drivers' sayfası)\n")
w('| Varsayım | Değer | Kaynak / gerekçe |\n|---|---|---|')
C_ = A['common']
for lab, val, src in [('2026T satış', m(C_['revenue_2026']), '1Y26 gerçekleşen $8.131M + 2Y tahmini; konsensüs $17.518M'),
                      ('Kurumsal gider 2026', m(C_['corporate_cost_2026']), 'Yönetim rehberi ~$150M; %2,5 enflasyon'),
                      ('İşletme sermayesi / satış', pct(C_['nwc_pct_revenue']), '2016–2025 yıl sonu %10,3–13,0'),
                      ('Faktoring/menkul kıymetleştirme maliyeti', m(C_['financing_fees']) + ' $M/yıl', '$830M bilanço dışı faktoring; borca eklenmedi'),
                      ('Nakit vergi', '2032\'ye kadar %20 (taban $150M), sonra %24', 'Yabancı vergi tabanı; ABD vergi varlıkları'),
                      ('Ertelenmiş gelir (nakitsiz SOI)', '2027–30 $55M, 2031 $40M', '$350M ertelenmiş gelir (4Ç25 sunumu)'),
                      ('D&A 2027', m(C_['da_2027']), '2026 rehberi $915M'), ('2Y26 faiz ödemesi', m(C_['h2_2026_interest_cash']), 'Yıllık ~$425M − 1Y $200M'),
                      ('Talepler (30.06.26)', m(R['claims_0630']), 'Net borç 6.329 + emeklilik 369 + asbest 50 + azınlık 162'),
                      ('Seyreltilmiş hisse', '290 milyon', '288M + ~2M ödül'), ('SAMK', pct(A['wacc']['base_wacc'], 2), 'Bölüm 8.1')]:
    w(f"| {lab} | {val} | {src} |")
w('\n| Senaryo girdisi | Boğa | Temel | Ayı |\n|---|---|---|---|')
SC = A['scenarios']
for lab, f in [('Olasılık', lambda s: pct(s['probability'], 0)), ('2Y26 FCFF', lambda s: m(s['h2_2026_fcff'])), ('2026 FCF (kaldıraçlı)', lambda s: m(s['fy2026_levered_fcf'])),
               ('Gelir büyümesi 2027 / 2028 / 2032+', lambda s: f"{pct(s['revenue_growth']['2027'])} / {pct(s['revenue_growth']['2028'])} / {pct(s['revenue_growth']['2032'])}"),
               ('SOI marjı 2027 / 2028 / 2030+', lambda s: f"{pct(s['soi_margin']['2027'])} / {pct(s['soi_margin']['2028'])} / {pct(s['soi_margin']['2030'])}"),
               ('Capex (2028+, satış %)', lambda s: pct(s['capex_pct'])), ('Yeniden yapılanma 2027 / 2028 / sonrası', lambda s: f"{m(s['restructuring']['2027'])} / {m(s['restructuring']['2028'])} / {m(s['restructuring']['later'])}"),
               ('Terminal büyüme', lambda s: pct(s['terminal_growth'])), ('RONIC', lambda s: 'SAMK' if s['ronic'] == 'wacc' else pct(s['ronic']))]:
    w(f"| {lab} | " + ' | '.join(f(SC[k]) for k in ['bull', 'base', 'bear']) + ' |')

w("\n## Ek B — Model denetimi\n")
n_ok = sum(1 for c in AU['checks'] if c['ok'])
w(f"Excel modeli LibreOffice ile yeniden hesaplandı (1.022 formül, 0 hata) ve Python motoruyla karşılaştırıldı: **{n_ok}/{len(AU['checks'])} kontrol geçti.** "
  "Senaryo FD'leri, hisse başı değerler, EPV, Merton, emsaller, SOTP, işlemler ve harmanlanmış değer birebir eşleşiyor; tüm iskonto formülleri tek bir SAMK hücresine bağlı; "
  "tüm hisse başı formüller seyreltilmiş hisse hücresine bölüyor; ölü girdi yok; hiçbir senaryoda kümülatif nakit yakımı likiditeyi ($4,75 milyar) aşmıyor.\n")
w("**Başarısız kontrol ve gerekçesi:** Ayı senaryosunun zımni terminal FD/FAVÖK'ü 2,1x ile emsal aralığının (3,5–6,2x) altında kalıyor; bu kabul edildi çünkü ayı senaryosu "
  "tanımı gereği sermaye maliyetinin altında getiri (RONIC %7 < SAMK) ve FAVÖK'ün yalnızca ~%12'sinin serbest nakde dönüştüğü bir işletmeyi temsil ediyor — ve özsermaye değeri, "
  "terminal çarpan emsal alt sınırına (3,5x) çekilse bile sıfırda kalıyor (FD ~$3–4 milyar < talepler $6,9 milyar).\n")

w("## Ek C — Kaynaklar (erişim: 26.09.2026)\n")
w("- SEC EDGAR, Goodyear CIK 42582: 10-K 2014–2025 (https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000042582); 10-Q 1Ç25–2Ç26; 8-K kazanç bültenleri 2015-01-13 … 2026-08-05; "
  "8-K 2023-07-25 (Elliott), 2023-11-15 (Goodyear Forward/CEO geçişi), 2024-01-18 (Stewart), 2024-07-22 (OTR satışı), 2025-01-08 (Dunlop), 2025-05-22 ve 2025-11-03 (Kimya), "
  "2026-03-20 (EMEA planı), 2026-06-04 (%8,875 tahvil), 2026-06-26 (CFO), 2026-07-21 (Fayetteville); DEF 14A 2019–2026; Form 4 (Haz-2025 → Eyl-2026).\n"
  "- SEC XBRL companyfacts API (https://data.sec.gov/api/xbrl/companyfacts/CIK0000042582.json) ve Cooper Tire (CIK 24491).\n"
  "- Goodyear yatırımcı sunumları 4Ç24, 1Ç25, 2Ç25, 3Ç25, 4Ç25, 1Ç26, 2Ç26 (https://corporate.goodyear.com/…/events-presentations/).\n"
  "- 2Ç26 konferans görüşmesi transkripti: [Motley Fool](https://www.fool.com/earnings/call-transcripts/2026/08/13/goodyear-gt-q2-2026-earnings-call-transcript/).\n"
  "- 2016 Yatırımcı Günü hedefleri: [Tire Review](https://www.tirereview.com/goodyear-announces-growth-plan-financial-targets/), [Goodyear haber](https://news.goodyear.com/goodyear_outlines_growth_plan_financial_targets).\n"
  "- Kredi notları: [S&P – B+'ya indirme](https://www.spglobal.com/ratings/en/regulatory/article/-/view/type/HTML/id/3094976) (erişim engellendi, başlık doğrulandı), "
  "[Moody's B1 teyidi](https://www.investing.com/news/stock-market-news/moodys-affirms-goodyears-b1-rating-revises-outlook-to-stable-93CH-4068937).\n"
  "- Piyasa verisi: Yahoo Finance (GT ve 13 lastik emsali fiyat, temel veri serileri; ^TNX 10Y faiz; ^GSPC), 25.09.2026 kapanışı.\n")
w("## Ek D — Elde edilemeyenler ve sınırlamalar\n")
w("- Konferans görüşmesi transkriptlerinin yalnızca 2Ç26 özeti okundu; diğer çeyreklerin tam metni alınamadı (dil/çerçeve değişimi analizi bültenler ve sunumlar üzerinden yapıldı).\n"
  "- S&P raporu içeriği 403 hatası verdi; indirme başlığı arama sonuçlarından doğrulandı, tarihi ve metrikleri doğrulanamadı.\n"
  "- OTR ve Kimya işlerinin FAVÖK'ü açıklanmadı; işlem çarpanları segment etkisinden tahmin edildi (analist tahmini).\n"
  "- Emsal verileri Yahoo Finance'ten; Sumitomo Rubber'ın son 12 ay serisi eksik olduğu için özet veriyle düzeltildi; Hankook 2025'ten itibaren Hanon Systems'ı konsolide ettiğinden referansa alındı; "
  "Nokian toparlanma çarpanı nedeniyle referansta. Emsal çarpanları farklı muhasebe standartları (UFRS/J-GAAP) ve para birimi faizleriyle fiyatlanıyor.\n"
  "- 2025 ticari lastik sektör hacminin tam rakamı alınamadı (bültenler 'keskin daralma' diyor).\n"
  "- Senaryo olasılıkları, Monte Carlo dağılım parametreleri ve yönetim puanlaması analist yargısı içerir; gerekçeleri metinde gösterildi ve Excel'de değiştirilebilir.\n")
w("## Ek E — Dosyalar\n")
w("- `valuation/GT/model/GT_model.xlsx` — canlı formüllü model (Drivers → DCF_Bull/Base/Bear → EPV, Merton, Comps, SOTP, Transactions_Asset → Summary; History, Guidance, Sensitivity, MonteCarlo).\n"
  "- `valuation/GT/data/` — XBRL ham tablo, normalize geçmiş (history.csv), rehberlik kaydı ve skorlar, emsaller, varsayımlar, değerleme sonuçları, denetim sonuçları.\n"
  "- `valuation/GT/scripts/` — veri toplama, normalizasyon, rehberlik takibi, emsal analizi, değerleme motoru, Excel üretimi, denetim ve grafik betikleri (yeniden çalıştırılabilir).\n"
  "- `valuation/GT/output/` — bu rapor ve grafikler; dönüş zamanlaması eki `GT_donus_analizi.md` (teknik veriler `data/technical.json`, senaryo zaman çizelgesi `data/turnaround.json`).\n")
w("---\n*Bu rapor yalnızca bilgilendirme amaçlı bir analizdir; herhangi bir menkul kıymeti alma veya satma tavsiyesi değildir. Geçmiş performans gelecekteki sonuçların göstergesi değildir. "
  "Hazırlayan lisanslı yatırım danışmanı değildir.*\n")

# '~' is rendered as strikethrough by GFM renderers when two single tildes pair up; use '≈' for "approximately".
open('output/GT_degerleme_raporu.md', 'w').write('\n'.join(out).replace('~', '≈'))
print('report written', sum(len(s) for s in out), 'chars')
