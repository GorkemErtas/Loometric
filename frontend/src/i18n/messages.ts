// English source IDs and Turkish translations. Keep placeholders identical.
export const messages = {
  "· Same demand verified by the backend. These are hypothetical planning changes, not observed productivity improvements.":
    "· Aynı talep, sunucu tarafından doğrulandı. Bunlar varsayımsal planlama değişiklikleridir; gözlemlenmiş verimlilik artışı değildir.",
  "Baseline producer & proof": "Referans yöntemi ve çözüm kanıtı",
  "Scenario producer & proof": "Senaryo yöntemi ve çözüm kanıtı",
  "Inspect verified schedule": "Doğrulanmış çizelgeyi incele",
  "Baseline · {p0}": "Referans · {p0}",
  "Scenario · {p0}": "Senaryo · {p0}",
  "{p0} verified Gantt": "{p0} doğrulanmış Gantt çizelgesi",
  Baseline: "Referans",
  Scenario: "Senaryo",
  "Advanced same-instance algorithm comparisons":
    "Aynı örnekte ayrıntılı algoritma karşılaştırmaları",
  "INVALID: independent verification rejected this proposal. No Gantt or performance metrics are accepted. {p0}":
    "GEÇERSİZ: bağımsız doğrulama bu öneriyi reddetti. Gantt çizelgesi ve performans ölçütleri kabul edilmedi. {p0}",
  "Allocated blocks come from independently verified backend results":
    "Atanan bloklar bağımsız olarak doğrulanmış sunucu sonuçlarından alınır",
  "Time axis · exact reported horizon": "Zaman ekseni · bildirilen planlama ufku",
  "SYNTHETIC · {p0}": "SENTETİK · {p0}",
  "{p0}: allocated operations by production line": "{p0}: üretim hatlarına atanan operasyonlar",
  "Production line": "Üretim hattı",
  "Declared shift {p0}: {p1} → {p2}": "Tanımlı vardiya {p0}: {p1} → {p2}",
  "{p0}: {p1} → {p2}": "{p0}: {p1} → {p2}",
  "Inspect operation {p0} {p1} on {p2}, {p3} pieces, {p4} to {p5}":
    "{p2} hattındaki {p0} {p1} operasyonunu incele: {p3} adet, {p4} – {p5}",
  "{p0} · {p1} · {p2} → {p3}": "{p0} · {p1} · {p2} → {p3}",
  "Verified allocation": "Doğrulanmış atama",
  "Declared shift window": "Tanımlı vardiya aralığı",
  "Declared interruption": "Tanımlı kesinti",
  " and the backend’s approved change audit": " ve sunucunun onayladığı değişiklik kaydı",
  "Positions use absolute timestamp geometry only. Blocks are not moved, resized or rescheduled. Calendar annotations use declared inputs{p0}. Use the table for exact times and on small screens.":
    "Konumlar yalnızca mutlak zaman damgalarına göre gösterilir. Bloklar taşınmaz, yeniden boyutlandırılmaz veya çizelgelenmez. Takvim açıklamaları tanımlı girdileri{p0} kullanır. Kesin zamanlar ve küçük ekranlar için tabloyu kullanın.",
  "No verified allocations": "Doğrulanmış atama yok",
  "The verified partial plan contains no allocated operations; all work remains explicit below.":
    "Doğrulanmış kısmi planda atanmış operasyon yoktur; kalan işlerin tamamı aşağıda gösterilir.",
  "Structured operation table ({p0})": "Operasyon tablosu ({p0})",
  "{p0} operation table": "{p0} operasyon tablosu",
  "Order / stage": "Sipariş / aşama",
  "Line / assignment": "Hat / atama",
  "Start → end (source offsets)": "Başlangıç → bitiş (kaynak saat farkları)",
  Pieces: "Adet",
  "Elapsed min": "Geçen süre (dk)",
  Details: "Ayrıntılar",
  "Operation details {p0} {p1}": "{p0} {p1} operasyon ayrıntıları",
  Inspect: "İncele",
  "Order completion & unfinished work": "Sipariş tamamlanma durumu ve kalan işler",
  "Finished units require all stages. A valid partial plan leaves demand unfinished.":
    "Tamamlanan adetler tüm aşamalardan geçmiş olmalıdır. Geçerli bir kısmi planda karşılanmamış talep kalabilir.",
  "Verified order outcomes": "Doğrulanmış sipariş sonuçları",
  Order: "Sipariş",
  Outcome: "Sonuç",
  "Finished pieces": "Tamamlanan adet",
  "Unfinished pieces": "Kalan adet",
  "Allocated stages / completion": "Atanan aşamalar / tamamlanma",
  "None allocated": "Atama yok",
  "No completed-order timestamp": "Sipariş tamamlanma zamanı yok",
  UNSCHEDULED: "ÇİZELGELENMEDİ",
  "{p0} pieces": "{p0} adet",
  "All required operations are allocated.": "Gerekli tüm operasyonlar atandı.",
  "Operation {p0} · {p1}": "Operasyon {p0} · {p1}",
  "Shift / profile": "Vardiya / profil",
  Quantity: "Miktar",
  "Exact reported interval": "Bildirilen kesin zaman aralığı",
  "Elapsed duration from endpoints": "Başlangıç ve bitiş arasındaki süre",
  "{p0} minutes": "{p0} dakika",
  "Reported reserved labor": "Bildirilen ayrılmış işçilik",
  "{p0} worker-minutes": "{p0} işçi-dakika",
  "Reported standard capacity": "Bildirilen standart kapasite",
  "{p0} standard worker-minutes": "{p0} standart işçi-dakika",
  "Verified synthetic allocation. No drag-and-drop editing or inferred machine availability.":
    "Doğrulanmış sentetik atama. Sürükleyip bırakma veya varsayılan makine kullanılabilirliği uygulanmaz.",
  "Connect the local API to execute planning workflows. Fixture preview never starts a scheduler or job.":
    "Planlama işlemlerini çalıştırmak için yerel API'ye bağlanın. Örnek veri önizlemesi çizelgeleyici veya iş başlatmaz.",
  "Loading the local session / selected capacity…": "Yerel oturum / seçili kapasite yükleniyor…",
  "No accepted metrics": "Kabul edilmiş ölçüt yok",
  "Invalid or missing results do not receive invented performance metrics.":
    "Geçersiz veya eksik sonuçlar için performans ölçütü üretilmez.",
  "Finished units": "Tamamlanan adet",
  "All required stages completed": "Gerekli tüm aşamaları tamamlanan",
  "Unfinished units": "Kalan adet",
  "Includes all incomplete order demand": "Tamamlanmamış sipariş talebinin tamamı",
  "Line utilization": "Hat kullanım oranı",
  "{p0} / {p1} net line-minutes": "{p0} / {p1} net hat-dakika",
  "Standard capacity use": "Standart kapasite kullanımı",
  "{p0} / {p1} standard worker-minutes": "{p0} / {p1} standart işçi-dakika",
  "Selection and proof are different claims":
    "Yöntem seçimi ve optimalite kanıtı farklı iddialardır",
  "Selected: {p0}": "Seçilen: {p0}",
  "full lexicographic proof": "tam leksikografik optimalite kanıtı",
  "no full lexicographic claim": "tam leksikografik optimalite iddiası yok",
  "Selected-plan proof: {p0} / 3 objectives · {p1}": "Seçili planın kanıtı: {p0} / 3 amaç · {p1}",
  "Fallback / retention reason:": "Referansa dönüş / mevcut çözümü koruma nedeni:",
  "Not required — verified candidate was strictly better":
    "Gerekmedi — doğrulanmış aday kesin olarak daha iyiydi",
  "Advanced optimizer evidence ({p0})": "Ayrıntılı optimizasyon kanıtı ({p0})",
  "Attempt / native status": "Deneme / çözücü durumu",
  "Not run / unavailable": "Çalıştırılmadı / mevcut değil",
  "Solver version": "Çözücü sürümü",
  "Not reported": "Bildirilmedi",
  "Candidate proof": "Aday çözümün kanıtı",
  "{p0} / 3 · full: {p1}": "{p0} / 3 · tam kanıt: {p1}",
  "Incumbent source": "Mevcut en iyi çözümün kaynağı",
  "No incumbent": "Mevcut çözüm yok",
  "Phase {p0}{p1}": "Faz {p0}{p1}",
  " — retained earlier incumbent": " — önceki en iyi çözüm korundu",
  "No accepted optimizer incumbent or candidate metrics are available. A resource stop or UNKNOWN is not proof of infeasibility.":
    "Kabul edilmiş optimizasyon çözümü veya aday ölçütleri yok. Kaynak sınırına ulaşılması ya da UNKNOWN durumu, uygunsuzluk kanıtı değildir.",
  "CP-SAT proof phases": "CP-SAT kanıt fazları",
  Phase: "Faz",
  Objective: "Amaç",
  "Native status": "Çözücü durumu",
  "Value / bound": "Değer / sınır",
  Proven: "Kanıtlandı",
  "FEASIBLE remains unproven. Candidate proof is never transferred to a selected greedy schedule. Objective order: unfinished pieces → completed-order priority-weighted tardiness → makespan.":
    "FEASIBLE durumu optimaliteyi kanıtlamaz. Adayın kanıtı seçilen açgözlü çizelgeye aktarılmaz. Amaç sırası: kalan adet → tamamlanan siparişlerde öncelik ağırlıklı gecikme → toplam tamamlanma süresi.",
  "Greedy vs selected result": "Açgözlü yöntem ile seçilen sonuç",
  "Same instance, frozen objective order; backend-provided metrics":
    "Aynı örnek, sabit amaç sırası; sunucunun bildirdiği ölçütler",
  "Algorithm metric comparison": "Algoritma ölçütlerinin karşılaştırması",
  "Metric / unit": "Ölçüt / birim",
  "Verified greedy": "Doğrulanmış açgözlü yöntem",
  "Selected {p0}": "Seçilen {p0}",
  "Optimizer candidate": "Optimizasyon adayı",
  "Candidate vs greedy: {p0}": "Aday / açgözlü yöntem: {p0}",
  "None — tie": "Yok — eşit",
  "Deciding objective: {p0}": "Kararı belirleyen amaç: {p0}",
  "Backend comparison supplies objective differences only; unreported same-instance percentage differences are not invented.":
    "Sunucu karşılaştırması yalnızca amaç farklarını bildirir; aynı örnek için bildirilmeyen yüzdelik farklar hesaplanmaz.",
  "No accepted candidate comparison is available. The selected verified greedy result remains explicit.":
    "Kabul edilmiş aday karşılaştırması yok. Doğrulanmış açgözlü yöntem sonucu açıkça korunur.",
  "Baseline vs scenario": "Referans ve senaryo",
  "Backend-provided scenario-minus-baseline deltas; conditional synthetic planning":
    "Sunucunun bildirdiği senaryo eksi referans farkları; koşullu sentetik planlama",
  "Greedy-only relation: {p0}": "Yalnızca açgözlü yöntem ilişkisi: {p0}",
  "Scenario metric differences": "Senaryo ölçüt farkları",
  "Absolute Δ": "Mutlak Δ",
  "Relative Δ": "Göreli Δ",
  "Not applicable": "Uygulanamaz",
  "{p0} percentage points": "{p0} yüzde puan",
  "Not applicable · {p0}": "Uygulanamaz · {p0}",
  "Tardiness covers completed orders only. Compare unfinished demand first. Utilization denominators can change; greater hypothetical capacity does not guarantee a better schedule or observed productivity.":
    "Gecikme yalnızca tamamlanan siparişleri kapsar. Önce karşılanmamış talebi karşılaştırın. Kullanım oranı paydaları değişebilir; varsayımsal kapasite artışı daha iyi bir çizelgeyi veya gözlemlenmiş verimlilik artışını garanti etmez.",
  "Verified change audit & identities ({p0} changes)":
    "Doğrulanmış değişiklik kaydı ve kimlikler ({p0} değişiklik)",
  "Baseline fingerprint": "Referans parmak izi",
  "Derived scenario ID / fingerprint": "Türetilen senaryo kimliği / parmak izi",
  "Specification fingerprint": "Değişiklik tanımının parmak izi",
  "Verified same-demand fingerprint": "Doğrulanmış ortak talep parmak izi",
  "explicit no-op": "açıkça etkisiz değişiklik",
  "Change {p0} before and after": "{p0}. değişikliğin öncesi ve sonrası",
  "{p0} result": "{p0} sonucu",
  "RESEARCH CANDIDATE": "ARAŞTIRMA ADAYI",
  BASELINE: "REFERANS",
  EXPERIMENTAL: "DENEYSEL",
  "Standard capacity attainment · dimensionless ratio":
    "Standart kapasite gerçekleşme oranı · boyutsuz oran",
  "Descriptive error band": "Betimsel hata aralığı",
  "{p0} to {p1}": "{p0} – {p1}",
  "Training out-of-fold P90 residual radius. Uncalibrated; no coverage guarantee. Retained benchmark coverage: {p0}.":
    "Eğitimde kat dışı P90 artık yarıçapı. Kalibre edilmemiştir; kapsama garantisi yoktur. Saklanan kıyaslama kapsamı: {p0}.",
  "Research evidence · EXP-008": "Araştırma bulguları · EXP-008",
  "24.05% lower retained benchmark MAE compared with Forest12.":
    "Saklanan kıyaslamada Forest12'ye göre %24,05 daha düşük MAE.",
  "Spent validation only. Stage and worst-error gates remain unresolved. No independently calibrated prediction band is available.":
    "Yalnızca daha önce incelenmiş doğrulama verileri. Aşama ve en yüksek hata eşikleri hâlâ karşılanmıyor. Bağımsız olarak kalibre edilmiş tahmin aralığı yok.",
  "Mature context · EXP-010": "Olgunlaşmış geçmiş bağlamı · EXP-010",
  "One frozen residual candidate using earlier same-crew/line reports. Missing or stale context abstains.":
    "Aynı ekip ve hattın önceki raporlarını kullanan, dondurulmuş tek bir artık modeli adayı. Eksik veya güncelliğini yitirmiş bağlamda tahmin üretilmez.",
  "Held-out gains include additional information and new development data. No calibrated band or factory validity.":
    "Ayrılmış verideki kazanımlar ek bilgi ve yeni geliştirme verilerini de içerir. Kalibre edilmiş aralık veya fabrika geçerliliği yoktur.",
  "Matched baseline MAE": "Eşleştirilmiş temel koşul MAE",
  "Validation MAE": "Doğrulama MAE",
  "matched baseline held-out rows; equal-world macro metrics":
    "eşleştirilmiş ayrılmış temel koşul satırı; dünyalara eşit ağırlık veren makro ölçütler",
  "benchmark validation rows": "kıyaslama doğrulama satırı",
  "{p0} {p1}; synthetic only.": "{p0} {p1}; yalnızca sentetik veri.",
  "Selected stage: MAE {p0}, n={p1}.": "Seçilen aşama: MAE {p0}, n={p1}.",
  "Failed promotion gates": "Karşılanmayan kullanıma geçiş eşikleri",
  "Maximum stage regression: +{p0}. Worst-error change: {p1}.":
    "En yüksek aşama gerilemesi: +{p0}. En yüksek hata değişimi: {p1}.",
  "Matched fresh-world evidence · EXP-010": "Yeni dünyalarda eşleştirilmiş bulgular · EXP-010",
  "All five models scored the same held-out observations. Metrics are equal-world macro averages; max error is the actual condition-wide maximum.":
    "Beş model de aynı ayrılmış gözlemlerde değerlendirildi. Ölçütler dünyalara eşit ağırlık veren makro ortalamalardır; en yüksek hata ilgili koşulun tamamındaki gerçek maksimumdur.",
  "Four new simulated worlds, {p0} residual training rows, one fit and no parameter search. History Boost uses additional mature reports; this comparison does not isolate algorithm quality. Published holdout outcomes are now inspected.":
    "Dört yeni simülasyon dünyası, {p0} artık eğitimi satırı, tek eğitim ve parametre araması yok. History Boost ek olgunlaşmış raporlar kullanır; bu karşılaştırma yalnızca algoritma kalitesini ölçmez. Yayımlanan ayrılmış veri sonuçları artık incelenmiştir.",
  "Matched held-out model metrics": "Eşleştirilmiş ayrılmış veri model ölçütleri",
  Model: "Model",
  Condition: "Koşul",
  Bias: "Yanlılık",
  "P95 abs": "Mutlak hata P95",
  "Max abs": "En yüksek mutlak hata",
  "Known limits: the candidate's actual worst baseline error increased 9.11% versus RF Physics. Missing-history control was worse under disruption; first unannounced shocks remain uncertain. NO_ML_PROMOTION applies to every model.":
    "Bilinen sınırlar: adayın temel koşuldaki gerçek en yüksek hatası RF Physics'e göre %9,11 arttı. Geçmişsiz kontrol modeli aksama koşulunda daha kötüydü; habersiz ilk şoklar belirsizliğini koruyor. NO_ML_PROMOTION tüm modeller için geçerlidir.",
  "Same-input model comparison": "Aynı girdide model karşılaştırması",
  "Signed differences in attainment ratio; no model is operationally promoted.":
    "Gerçekleşme oranındaki işaretli farklar; hiçbir model operasyonel kullanıma alınmamıştır.",
  "Model prediction differences": "Model tahmin farkları",
  "Left model": "Sol model",
  "Right model": "Sağ model",
  "Left minus right": "Sol eksi sağ",
  "Global Random Forest behavior": "Random Forest genel davranışı",
  "Computed training impurity importance, aggregated over one-hot categories.":
    "Eğitimde hesaplanan, tek-sıcak kategoriler üzerinden birleştirilmiş safsızlık önemleri.",
  "This describes the fitted forest globally. It does not explain this individual prediction. Correlated inputs and feature cardinality can distort importance. No causal or SHAP explanation is claimed.":
    "Bu görünüm eğitilmiş ormanı genel olarak betimler; tekil tahmini açıklamaz. İlişkili girdiler ve özelliklerin kategori sayıları önemleri çarpıtabilir. Nedensel açıklama veya SHAP açıklaması iddiası yoktur.",
  "Model provenance and research limits": "Model kökeni ve araştırma sınırları",
  "Published synthetic research evidence; NO_ML_PROMOTION remains in force.":
    "Yayımlanmış sentetik araştırma bulguları; NO_ML_PROMOTION geçerliliğini korur.",
  "{p0} · {p1} · {p2} original training rows ({p3} to {p4}).":
    "{p0} · {p1} · {p2} özgün eğitim satırı ({p3} – {p4}).",
  "Manifest SHA-256": "Manifest SHA-256",
  "EXP-008 research candidate manifest SHA-256": "EXP-008 araştırma adayı manifest SHA-256",
  "Training payload": "Eğitim veri yükü",
  "Input receipt": "Girdi makbuzu",
  "Whole isolated request: {p0} seconds, including startup, integrity checks and model loading.":
    "Yalıtılmış isteğin tamamı: başlatma, bütünlük kontrolleri ve model yükleme dâhil {p0} saniye.",
  "Hypothetical scenario comparison": "Varsayımsal senaryo karşılaştırması",
  "A pinned API response and a new request. Differences are not proven causal effects.":
    "Sabitlenmiş bir API yanıtı ve yeni bir istek. Farkların nedensel etki olduğu kanıtlanmamıştır.",
  "Before: saved in this tab from a real API response. Modify one or more inputs, then predict again.":
    "Önce: gerçek bir API yanıtından bu sekmeye kaydedildi. Bir veya daha fazla girdiyi değiştirip yeniden tahmin edin.",
  "No input differences between these requests.": "Bu istekler arasında girdi farkı yok.",
  "Scenario input differences": "Senaryo girdi farkları",
  Input: "Girdi",
  Before: "Önce",
  After: "Sonra",
  "Before and after model predictions": "Önceki ve sonraki model tahminleri",
  "After minus before": "Sonra eksi önce",
  "After support": "Sonraki destek durumu",
  "Only models present in both requests are compared. No schedule or capacity profile is changed.":
    "Yalnızca iki istekte de bulunan modeller karşılaştırılır. Çizelge veya kapasite profili değiştirilmez.",
  "Waiting for the next real prediction. No after value is assumed.":
    "Sonraki gerçek tahmin bekleniyor. Sonraki değer varsayılmaz.",
  "Choose explicitly": "Açıkça seçin",
  "Stage labor standards": "Aşama işçilik standartları",
  "Explicit breaks": "Tanımlı molalar",
  "A positive standard describes worker labor per piece, not elapsed machine time. Add each supported stage once.":
    "Pozitif standart, geçen makine süresini değil adet başına işçiliği tanımlar. Desteklenen her aşamayı bir kez ekleyin.",
  "No break rows explicitly means no breaks. Python checks containment and overlap; all times must be on the minute grid.":
    "Mola satırı eklenmemesi, mola olmadığı anlamına gelir. Python kapsama ve çakışmayı denetler; tüm zamanlar tam dakikaya hizalanmalıdır.",
  "Remove {p0} {p1}": "{p0} {p1} kaldır",
  Remove: "Kaldır",
  "Add stage standard": "Aşama standardı ekle",
  "Add break": "Mola ekle",
  "Ordered production stages": "Sıralı üretim aşamaları",
  "Whole batches follow this exact sequence. Every stage needs a standard on the selected style.":
    "Tam partiler bu sırayı izler. Seçili ürün modelinde her aşamanın standardı olmalıdır.",
  "Move stage {p0} earlier": "{p0}. aşamayı öne taşı",
  Earlier: "Öne taşı",
  "Move stage {p0} later": "{p0}. aşamayı sona taşı",
  Later: "Sona taşı",
  "Remove stage {p0}": "{p0}. aşamayı kaldır",
  "Add required stage": "Gerekli aşama ekle",
  "Choose stage": "Aşama seçin",
  "Append stage": "Sıraya ekle",
  "Save record": "Kaydı kaydet",
  "Cancel editing": "Düzenlemeyi iptal et",
  "No {p0} declared. Add records with explicit synthetic assumptions.":
    "{p0} tanımlanmadı. Açık sentetik varsayımlarla kayıt ekleyin.",
  "Edit {p0}": "{p0} düzenle",
  Edit: "Düzenle",
  "Remove {p0}": "{p0} kaldır",
  "Add {p0}": "{p0} ekle",
  "Working dates": "Çalışma tarihleri",
  "Declare each shift start date explicitly. Overnight shifts belong to their start date; no weekly calendar is inferred.":
    "Her vardiyanın başlangıç tarihini açıkça tanımlayın. Gece vardiyaları başladıkları güne aittir; haftalık takvim varsayılmaz.",
  "Remove working date {p0}": "{p0} çalışma tarihini kaldır",
  "Working date": "Çalışma tarihi",
  "Add working date": "Çalışma tarihi ekle",
  "This working date is already declared.": "Bu çalışma tarihi zaten tanımlı.",
  "Loading the local capacity report…": "Yerel kapasite raporu yükleniyor…",
  "Retry capacity request": "Kapasite isteğini yeniden dene",
  "Use Configure API to connect or replace the session.":
    "Bağlanmak veya oturumu değiştirmek için API ayarlarını kullanın.",
  "No capacity report loaded": "Kapasite raporu yüklenmedi",
  "Connect the local API to request a report for the selected dataset.":
    "Seçili veri kümesi için rapor istemek üzere yerel API'ye bağlanın.",
  "This input has no saved capacity preview. Connect the local API to assess it.":
    "Bu girdinin kayıtlı kapasite önizlemesi yok. Değerlendirmek için yerel API'ye bağlanın.",
  "Available elapsed minutes": "Kullanılabilir süre (dakika)",
  "Blocked minutes": "Bloke süre (dakika)",
  min: "dk",
  "Each bar is one assignment’s available / gross elapsed minutes. These slots are not allocated to orders.":
    "Her çubuk bir atamanın kullanılabilir / brüt süresini gösterir. Bu zaman dilimleri siparişlere atanmamıştır.",
  "Data provenance": "Veri kökeni",
  "Bundled fixture": "Paketlenmiş örnek veri",
  "API response": "API yanıtı",
  "Input only · no API report": "Yalnızca girdi · API raporu yok",
  "Source input": "Kaynak girdi",
  "Scenario ID": "Senaryo kimliği",
  "Source SHA-256 (LF-normalized text)": "Kaynak SHA-256 (LF ile normalleştirilmiş metin)",
  "Capacity request ID": "Kapasite isteği kimliği",
  "Planning assumptions ({p0})": "Planlama varsayımları ({p0})",
  "Request unavailable": "İstek tamamlanamadı",
  "Retry guidance: wait at least {p0} seconds.":
    "Yeniden denemeden önce en az {p0} saniye bekleyin.",
  "Request ID: {p0}": "İstek kimliği: {p0}",
  "Close dialog": "İletişim kutusunu kapat",
  "Connect to local API": "Yerel API'ye bağlan",
  "Enter the local API origin, or this site's configured HTTPS origin, and your session token.":
    "Yerel API adresini veya bu sitenin yapılandırılmış HTTPS adresini ve oturum anahtarınızı girin.",
  "API origin": "API adresi",
  "Bearer token": "Bearer anahtarı",
  "Kept in this tab’s memory only. Reloading or clearing the session removes it. Use a literal localhost/127.0.0.1 origin, or the current HTTPS site. Credentials stay in memory.":
    "Yalnızca bu sekmenin belleğinde tutulur. Sayfa yenilendiğinde veya oturum temizlendiğinde silinir. localhost/127.0.0.1 adresini ya da mevcut HTTPS sitesini kullanın. Kimlik bilgileri bellekte kalır.",
  Cancel: "İptal",
  "Connect & load capacity": "Bağlan ve kapasiteyi yükle",
  "Skip to content": "İçeriğe geç",
  "Workspace navigation": "Çalışma alanı gezinmesi",
  "PRODUCTION INTELLIGENCE": "ÜRETİM ANALİTİĞİ",
  WORKSPACE: "ÇALIŞMA ALANI",
  "Main navigation": "Ana gezinme",
  "LOCAL WORKSPACE": "YEREL ÇALIŞMA ALANI",
  "Synthetic planning data": "Sentetik planlama verileri",
  "No live factory connection": "Canlı fabrika bağlantısı yok",
  "Toggle navigation": "Gezinme menüsünü aç/kapat",
  Workspace: "Çalışma alanı",
  "Configure API": "API ayarları",
  "PRODUCTION WORKSPACE": "ÜRETİM ÇALIŞMA ALANI",
  "Planning dataset": "Planlama veri kümesi",
  "No datasets available": "Kullanılabilir veri kümesi yok",
  "Changing dataset/session discards local job IDs. Copy them first; server jobs may continue.":
    "Veri kümesi veya oturum değişikliği yerel iş kimliklerini siler. Önce kopyalayın; sunucudaki işler devam edebilir.",
  SYNTHETIC: "SENTETİK",
  "Experimental ML research": "Deneysel makine öğrenmesi araştırması",
  "Fixture preview": "Örnek veri önizlemesi",
  "Local API mode": "Yerel API modu",
  "synthetic-ml-v1 · independent of planning dataset":
    "synthetic-ml-v1 · planlama veri kümesinden bağımsız",
  "No dataset selected": "Veri kümesi seçilmedi",
  "Input-only preview · connect API for reports":
    "Yalnızca girdi önizlemesi · raporlar için API'ye bağlanın",
  "Loometric · Local production planning": "Loometric · Yerel üretim planlama",
  "Inputs, capacity estimates and verified schedules are labeled separately.":
    "Girdiler, kapasite tahminleri ve doğrulanmış çizelgeler ayrı ayrı etiketlenir.",
  "Available elapsed time": "Kullanılabilir süre",
  "Sum across unique assignment slots": "Benzersiz atama dilimlerinin toplamı",
  "Available crew time": "Kullanılabilir ekip süresi",
  "Effective standard capacity": "Etkin standart kapasite",
  "standard worker-minutes": "standart işçi-dakika",
  "Reported capacity using assumed efficiency": "Varsayılan verimlilikle bildirilen kapasite",
  "Capacity by assignment": "Atama bazında kapasite",
  "Available time after the union of declared blocked intervals":
    "Tanımlı bloke aralıkların birleşimi çıkarıldıktan sonra kullanılabilir süre",
  "Capacity report scrollable table": "Yatay kaydırılabilir kapasite raporu tablosu",
  "Assignment / line": "Atama / hat",
  "Stage / shift": "Aşama / vardiya",
  Crew: "Ekip",
  "Available min": "Kullanılabilir dk",
  "Standard worker-min": "Standart işçi-dk",
  "Blocked min": "Bloke dk",
  "Breaks: {p0} min": "Molalar: {p0} dk",
  "Additional downtime: {p0} min": "Ek duruş: {p0} dk",
  "Additional unavailable: {p0} min": "Ek kullanılamayan süre: {p0} dk",
  "No capacity slots": "Kapasite dilimi yok",
  "This report contains no line–shift assignments.": "Bu raporda hat–vardiya ataması yok.",
  "Independent output assessments": "Bağımsız çıktı değerlendirmeleri",
  "Potential pieces for one order stage in one slot, considered in isolation":
    "Tek bir sipariş aşamasının tek bir dilimde, diğer işlerden bağımsız potansiyel adedi",
  "Filter assessments by order": "Değerlendirmeleri siparişe göre filtrele",
  "All orders": "Tüm siparişler",
  "Compatible routes only": "Yalnızca uyumlu rotalar",
  "{p0} assessments": "{p0} değerlendirme",
  "Order / style": "Sipariş / ürün modeli",
  Stage: "Aşama",
  "Slot / line": "Dilim / hat",
  "Potential pieces": "Potansiyel adet",
  "Required standard min": "Gerekli standart dk",
  "Independent check": "Bağımsız kontrol",
  "Fits independently": "Bağımsız olarak yeterli",
  Restricted: "Kısıtlı",
  "No restriction codes": "Kısıtlama kodu yok",
  "No matching assessments": "Eşleşen değerlendirme yok",
  "Adjust the order or route compatibility filter.":
    "Sipariş veya rota uyumluluğu filtresini değiştirin.",
  "Assessment boundaries": "Değerlendirme sınırları",
  "Independent capacity estimates · no allocation performed":
    "Bağımsız kapasite tahminleri · atama yapılmadı",
  "Independent assessment only.": "Yalnızca bağımsız değerlendirme.",
  "Multiple orders can each appear to fit the same slot. Potential outputs must not be added together or interpreted as a globally feasible schedule.":
    "Birden fazla sipariş aynı dilime tek başına sığıyor görünebilir. Potansiyel çıktılar toplanmamalı veya bütünsel olarak uygulanabilir bir çizelge gibi yorumlanmamalıdır.",
  "Selected job lifecycle": "Seçili işin yaşam döngüsü",
  "Actual server status and phase; no percentage progress":
    "Gerçek sunucu durumu ve fazı; yüzdelik ilerleme gösterilmez",
  "Copyable job ID": "Kopyalanabilir iş kimliği",
  "Job ID": "İş kimliği",
  "Polling sequentially · at least {p0} s between requests":
    "Sıralı durum sorgulama · istekler arasında en az {p0} sn",
  "Local polling stopped": "Yerel durum sorgulama durdu",
  " · cancellation request pending": " · iptal isteği bekleniyor",
  "Submitted / started (server timestamps)": "Gönderilme / başlama (sunucu zamanları)",
  "Not started": "Başlamadı",
  "Completed / retention deadline": "Tamamlanma / saklama sonu",
  "Not terminal": "Son duruma ulaşmadı",
  "Cancellation / retained result": "İptal / saklanan sonuç",
  "Stop requested": "Durdurma istendi",
  "No stop requested": "Durdurma istenmedi",
  "Server reports result available": "Sunucuya göre sonuç mevcut",
  "No server result available": "Sunucuda sonuç yok",
  "Failure category": "Hata kategorisi",
  "None reported": "Bildirim yok",
  "Latest metadata request ID": "Son üst veri isteği kimliği",
  "Resume / refresh status": "Sürdür / durumu yenile",
  "Pause local tracking": "Yerel takibi duraklat",
  "Requesting cancellation…": "İptal isteniyor…",
  "Cancel server job": "Sunucudaki işi iptal et",
  "Forget terminal local receipt": "Tamamlanmış yerel iş makbuzunu kaldır",
  "Volatile local jobs: one active, two waiting, at most 32 server records. This workspace retains at most eight receipts in this dataset/session. Server results expire after 300 seconds; restart loses records. Copy job IDs. Leaving this page pauses polling; changing dataset/session clears local tracking, not server work. There is no job-list or restart recovery endpoint.":
    "Geçici yerel işler: bir etkin, iki bekleyen iş ve en fazla 32 sunucu kaydı. Bu çalışma alanı, veri kümesi/oturum başına en fazla sekiz makbuzu tutar. Sonuçlar 300 saniye sonra silinir; sunucunun yeniden başlaması kayıtları kaybettirir. İş kimliklerini kopyalayın. Sayfadan ayrılmak sorgulamayı duraklatır; veri kümesi/oturum değişikliği sunucudaki işi değil yerel takibi temizler. İş listeleme veya yeniden başlatma sonrası kurtarma uç noktası yoktur.",
  "Session job receipts": "Oturumdaki iş makbuzları",
  "{p0} / 8 local receipts · IDs and results are kept only in memory":
    "{p0} / 8 yerel makbuz · kimlikler ve sonuçlar yalnızca bellekte tutulur",
  "Open scheduling →": "Çizelgelemeyi aç →",
  "Local job receipts": "Yerel iş makbuzları",
  Type: "Tür",
  "Server status / phase": "Sunucu durumu / fazı",
  "Inspect job {p0}": "{p0} işini incele",
  "No submitted jobs in this context": "Bu bağlamda gönderilmiş iş yok",
  "Run reference scheduling, then submit a bounded scheduling or reviewed what-if comparison job. A lost POST reply may leave work without a local receipt; POST is never retried automatically.":
    "Önce referans çizelgelemeyi çalıştırın; ardından sınırlı bir çizelgeleme veya incelenmiş senaryo karşılaştırma işi gönderin. Kaybolan POST yanıtı, işin yerel makbuz olmadan sürmesine yol açabilir; POST otomatik olarak yeniden denenmez.",
  "Verified job result": "Doğrulanmış iş sonucu",
  "Result request ID:": "Sonuç isteği kimliği:",
  "Measured whole-child wall seconds: {p0}": "Alt sürecin ölçülen toplam süresi: {p0} saniye",
  "Selected optimizer-job Gantt": "Seçili optimizasyon işinin Gantt çizelgesi",
  "All metrics & same-instance algorithm comparison":
    "Tüm ölçütler ve aynı örnekte algoritma karşılaştırması",
  "No planning dataset": "Planlama veri kümesi yok",
  "Choose a synthetic dataset first.": "Önce sentetik veri kümesi seçin.",
  "Order register": "Sipariş kayıtları",
  "{p0} unique orders · source inputs, not scheduled output":
    "{p0} benzersiz sipariş · kaynak girdiler, çizelgelenmiş çıktı değil",
  "Planning inputs": "Planlama girdileri",
  "Search orders": "Sipariş ara",
  "Search order, style or stage…": "Sipariş, ürün modeli veya aşama ara…",
  "{p0} of {p1} orders": "{p1} siparişten {p0} tanesi",
  "Order register scrollable table": "Yatay kaydırılabilir sipariş tablosu",
  "Synthetic order register. Activate a column header to change sort order.":
    "Sentetik sipariş kayıtları. Sıralamayı değiştirmek için sütun başlığını etkinleştirin.",
  "Required stages": "Gerekli aşamalar",
  "Inspect {p0}": "{p0} incele",
  "No matching orders": "Eşleşen sipariş yok",
  "Try another order ID, style or required stage.":
    "Başka bir sipariş kimliği, ürün modeli veya gerekli aşama deneyin.",
  "Priority is the declared input value; 1 is highest priority in the existing scheduling policy.":
    "Öncelik tanımlı girdi değeridir; mevcut çizelgeleme politikasında 1 en yüksek önceliktir.",
  "Routing below reflects declared line–style capabilities. Release dates, material readiness and shared capacity still require scheduling verification.":
    "Aşağıdaki rotalar tanımlı hat–ürün modeli yetkinliklerini gösterir. Başlangıç tarihleri, malzeme hazırlığı ve ortak kapasite hâlâ çizelge doğrulaması gerektirir.",
  "Order {p0}": "Sipariş {p0}",
  "SYNTHETIC INPUT": "SENTETİK GİRDİ",
  Style: "Ürün modeli",
  Priority: "Öncelik",
  "Release / due": "Başlangıç / teslim",
  "Declared routing compatibility": "Tanımlı rota uyumluluğu",
  "{p0} standard worker-minutes / piece · {p1}": "{p0} standart işçi-dakika / adet · {p1}",
  "No standard declared": "Standart tanımlanmadı",
  "No compatible line declared.": "Uyumlu hat tanımlanmadı.",
  "Capability does not mean this order has been allocated or can meet its due date.":
    "Yetkinlik, bu siparişin atandığı veya teslim tarihine yetişeceği anlamına gelmez.",
  "There are no synthetic inputs in this catalog.": "Bu katalogda sentetik girdi yok.",
  Orders: "Siparişler",
  "Declared planning demand": "Tanımlı planlama talebi",
  "Requested units": "Talep edilen adet",
  "Sum of unique order quantities": "Benzersiz sipariş miktarları toplamı",
  "Production lines": "Üretim hatları",
  "{p0} declared route capabilities": "{p0} tanımlı rota yetkinliği",
  Shifts: "Vardiyalar",
  "{p0} line–shift assignments": "{p0} hat–vardiya ataması",
  "Available capacity": "Kullanılabilir kapasite",
  "Explore capacity": "Kapasiteyi incele",
  "available worker-minutes across {p0} unique slots":
    "{p0} benzersiz dilimde kullanılabilir işçi-dakika",
  "Planning context": "Planlama bağlamı",
  "None declared": "Tanım yok",
  Styles: "Ürün modelleri",
  "Capacity basis": "Kapasite temeli",
  "Declared crews & assumed efficiency": "Tanımlı ekipler ve varsayılan verimlilik",
  "Allocation status": "Atama durumu",
  "Independent capacity checks can share the same slot. They do not establish a feasible production plan.":
    "Bağımsız kapasite kontrolleri aynı dilimi paylaşabilir. Bu kontroller uygulanabilir bir üretim planı oluşturmaz.",
  "Orders at a glance": "Siparişlere genel bakış",
  "Declared demand and delivery windows": "Tanımlı talep ve teslim aralıkları",
  "View all orders": "Tüm siparişleri gör",
  "Order summary scrollable table": "Yatay kaydırılabilir sipariş özet tablosu",
  "Quantity (pieces)": "Miktar (adet)",
  "Due date": "Teslim tarihi",
  "No declared orders": "Tanımlı sipariş yok",
  "This input contains no orders.": "Bu girdide sipariş yok.",
  "Existing scheduling outcome": "Mevcut çizelgeleme sonucu",
  "An outcome appears only after you explicitly load a previously saved proposal.":
    "Sonuç, yalnızca önceden kaydedilmiş öneriyi açıkça yüklediğinizde görünür.",
  "Reload saved outcome": "Kayıtlı sonucu yeniden yükle",
  "Load saved outcome": "Kayıtlı sonucu yükle",
  "Verifying the existing proposal with the local backend…":
    "Mevcut öneri yerel sunucuda doğrulanıyor…",
  "No schedule outcome loaded": "Çizelgeleme sonucu yüklenmedi",
  "This capacity fixture has no saved schedule. Use Production scheduling to run a verified reference schedule.":
    "Bu kapasite örneğinde kayıtlı çizelge yok. Doğrulanmış referans çizelge için Üretim çizelgeleme sayfasını kullanın.",
  "Completed units": "Tamamlanan adet",
  "Remaining declared order demand": "Tanımlı sipariş talebinin kalanı",
  "Synthetic verified scheduling metrics; utilization denominators come from the scheduling report. A partial result does not satisfy all demand.":
    "Sentetik, doğrulanmış çizelgeleme ölçütleri; kullanım oranlarının paydaları çizelgeleme raporundan gelir. Kısmi sonuç tüm talebi karşılamaz.",
  "No metrics are available for this invalid proposal. {p0}":
    "Bu geçersiz öneri için ölçüt yok. {p0}",
  "Verified instance fingerprint": "Doğrulanmış örnek parmak izi",
  "EXPERIMENTAL · SYNTHETIC ONLY": "DENEYSEL · YALNIZCA SENTETİK VERİ",
  "Explore planned production conditions": "Planlanan üretim koşullarını keşfedin",
  "Execute actual fitted models against hypothetical pre-shift inputs. Forecast standard capacity attainment, not guaranteed production output or intrinsic employee efficiency.":
    "Gerçek eğitilmiş modelleri varsayımsal vardiya öncesi girdilerle çalıştırın. Tahmin edilen değer standart kapasite gerçekleşme oranıdır; garanti edilen üretim çıktısı veya çalışanın öz verimliliği değildir.",
  "NO ML PROMOTION": "OPERASYONEL KULLANIM ONAYI YOK",
  "Research and demonstration": "Araştırma ve gösterim",
  "Human review required": "İnsan incelemesi gerekli",
  "Known subgroup failures remain visible.": "Bilinen alt grup başarısızlıkları görünür kalır.",
  "Forest12 packing MAE regressed 51.84% in development seed 19 (36 rows). Hist31 failed stage and worst-error gates. Lower aggregate MAE does not establish superiority in every stage.":
    "Forest12 paketleme MAE değeri, geliştirme tohumu 19'da %51,84 geriledi (36 satır). Hist31 aşama ve en yüksek hata eşiklerini geçemedi. Daha düşük genel MAE, her aşamada üstünlük göstermez.",
  "RF Physics · EXP-008.": "RF Physics · EXP-008.",
  "Retained benchmark MAE improved by 24.05% compared with Forest12. Stage-specific and worst-error regressions remain unresolved. EXP-009 prospective validation failed the complete replication criteria.":
    "Saklanan kıyaslama MAE değeri Forest12'ye göre %24,05 iyileşti. Aşama bazında ve en yüksek hatadaki gerilemeler çözülmedi. EXP-009 ileriye dönük doğrulaması tüm tekrarlama kriterlerini karşılayamadı.",
  "History Boost · EXP-010.": "History Boost · EXP-010.",
  "One fixed residual fit passed fresh held-out demonstration guards using mature past-shift context. Missing or stale history abstains. Baseline worst error still increased 9.11%; first unannounced shocks remain uncertain.":
    "Sabit tek artık eğitimi, olgunlaşmış geçmiş vardiya bağlamıyla yeni ayrılmış veri gösterim eşiklerini geçti. Eksik veya eski geçmişte tahmin üretilmez. Temel koşulda en yüksek hata yine %9,11 arttı; habersiz ilk şoklar belirsizliğini koruyor.",
  "Connect with Configure API to run actual models. Example inputs below are editable; no prediction is generated in preview mode.":
    "Gerçek modelleri çalıştırmak için API ayarlarından bağlanın. Aşağıdaki örnek girdiler düzenlenebilir; önizleme modunda tahmin üretilmez.",
  "Hypothetical pre-shift inputs": "Varsayımsal vardiya öncesi girdiler",
  "One order-stage on one dedicated crew and line. All values must be planned and available before shift start.":
    "Tek bir atanmış ekip ve hatta tek sipariş-aşama gözlemi. Tüm değerler planlanmış ve vardiya başlamadan biliniyor olmalıdır.",
  "MATURE HISTORY REQUIRED": "OLGUNLAŞMIŞ GEÇMİŞ GEREKLİ",
  "comparison baseline": "karşılaştırma referansı",
  "Compare all four original models": "İlk dört modeli karşılaştır",
  "Compare all five models": "Beş modelin tamamını karşılaştır",
  "Default: RF Physics, an experimental research candidate with lower retained benchmark MAE. No operational promotion or factory validation is implied.":
    "Varsayılan model RF Physics'tir; saklanan kıyaslamada daha düşük MAE sağlayan deneysel araştırma adayıdır. Operasyonel kullanım onayı veya fabrika doğrulaması anlamına gelmez.",
  "Production context": "Üretim bağlamı",
  "Production stage": "Üretim aşaması",
  "Single process stage for this observation.": "Bu gözlem için tek bir işlem aşaması.",
  Shift: "Vardiya",
  Day: "Gündüz",
  Night: "Gece",
  "Frozen planned shift type.": "Sabit planlı vardiya türü.",
  "Shift start weekday": "Vardiya başlangıç günü",
  "Local weekday of shift start, including for night shifts.":
    "Gece vardiyaları dâhil vardiyanın başladığı yerel gün.",
  "Mature historical context · optional fifth model":
    "Olgunlaşmış geçmiş bağlamı · isteğe bağlı beşinci model",
  "Use only the last seven same-crew and same-line reports available before the 30-minute pre-shift cutoff. Mean/std exclude past shifts whose output was limited by offered work. Leave missing history empty; History Boost will abstain. These editable values are hypothetical, not imported factory measurements.":
    "Yalnızca vardiyadan 30 dakika önceki kesim zamanında mevcut, aynı ekip ve hatta ait son yedi raporu kullanın. Ortalama ve standart sapma, çıktısı sunulan işle sınırlanmış geçmiş vardiyaları dışlar. Eksik geçmişi boş bırakın; History Boost tahmin üretmeyecektir. Düzenlenebilir bu değerler varsayımsaldır, fabrikadan alınmış ölçümler değildir.",
  "At least two uncensored reports and age ≤ 72 hours are required for a candidate point estimate.":
    "Adayın nokta tahmini için en az iki sansürlenmemiş rapor ve en fazla 72 saatlik geçmiş yaşı gerekir.",
  "Planned crew, time and demand": "Planlanan ekip, süre ve talep",
  "Planned machine available": "Planlanan makine kullanılabilir",
  "Unavailable machine or zero labor/time produces abstention.":
    "Makine kullanılamıyorsa veya işçilik/süre sıfırsa tahmin üretilmez.",
  "I am testing hypothetical synthetic pre-shift conditions.":
    "Varsayımsal, sentetik vardiya öncesi koşulları deniyorum.",
  "No measured factory accuracy or operational authorization is implied.":
    "Ölçülmüş fabrika doğruluğu veya operasyonel yetkilendirme iddiası yoktur.",
  "Check input consistency": "Girdi tutarlılığını kontrol edin",
  "Running actual estimators…": "Gerçek tahmin modelleri çalışıyor…",
  Predict: "Tahmin et",
  "Cancel request": "İsteği iptal et",
  "Use as scenario baseline": "Senaryo referansı olarak kullan",
  "Clear scenario baseline": "Senaryo referansını temizle",
  "Loading trusted models and computing predictions.":
    "Güvenilir modeller yükleniyor ve tahminler hesaplanıyor.",
  "API response · {p0}": "API yanıtı · {p0}",
  "No current prediction response.": "Güncel tahmin yanıtı yok.",
  "Publish the trusted local experimental artifacts using the documented offline setup, then retry.":
    "Belgelenen çevrimdışı kurulumla güvenilir yerel deneysel model dosyalarını hazırlayın, ardından yeniden deneyin.",
  "Your next prediction starts with a real request": "Sonraki tahmininiz gerçek bir istekle başlar",
  "Review the inputs and synthetic declaration, then predict. Editing inputs clears the current result; a pinned scenario baseline stays visible until the session changes.":
    "Girdileri ve sentetik kullanım beyanını inceleyip tahmin edin. Girdileri düzenlemek güncel sonucu temizler; sabitlenmiş senaryo referansı oturum değişene kadar görünür kalır.",
  "Planning assumptions": "Planlama varsayımları",
  "Set the horizon and fixed calendar offset before creating your resources. These are hypothetical production inputs.":
    "Kaynakları oluşturmadan önce planlama ufkunu ve sabit takvim saat farkını ayarlayın. Bunlar varsayımsal üretim girdileridir.",
  "Horizon start (with offset)": "Planlama ufku başlangıcı (saat farkıyla)",
  "Include seconds and an explicit offset. All boundaries align to whole minutes.":
    "Saniyeyi ve açık saat farkını ekleyin. Tüm sınırlar tam dakikaya hizalanmalıdır.",
  "Horizon end (with offset)": "Planlama ufku bitişi (saat farkıyla)",
  "Fixed calendar UTC offset (minutes)": "Sabit takvim UTC farkı (dakika)",
  "For example, enter 180 for +03:00, 0 for UTC, or -300 for -05:00. Shift starts must use this offset; no daylight-saving rules are inferred.":
    "Örneğin +03:00 için 180, UTC için 0, -05:00 için -300 girin. Vardiya başlangıçları bu farkı kullanmalıdır; yaz saati kuralları varsayılmaz.",
  "Synthetic planning assumptions (one per line)":
    "Sentetik planlama varsayımları (her satıra bir tane)",
  "Describe hypothetical standards, dedicated crews and efficiency. Only synthetic inputs belong here. Empty lines are errors.":
    "Varsayımsal standartları, atanmış ekipleri ve verimliliği açıklayın. Burada yalnızca sentetik girdiler kullanın. Boş satırlar hatadır.",
  "The frozen policy uses full batches and nonpreemptive stages on one qualified line, with release dates and ordered precedence. Materials, setups, shared crews, initial WIP and ML capacity are unsupported.":
    "Sabit politika; başlangıç tarihleri ve aşama sırasıyla, tek yetkin hatta tam partileri ve bölünemeyen aşamaları kullanır. Malzeme, hazırlık, ortak ekip, başlangıç yarı mamulü ve ML kapasitesi desteklenmez.",
  "Planning assumptions saved. Continue with product styles.":
    "Planlama varsayımları kaydedildi. Ürün modelleriyle devam edin.",
  "Save planning assumptions": "Planlama varsayımlarını kaydet",
  "Discard unsaved changes": "Kaydedilmemiş değişiklikleri geri al",
  "Your synthetic production input": "Sentetik üretim girdiniz",
  "Build a scheduling instance from forms, or edit a copy of an existing template. Work stays in this tab until you explicitly validate or activate it.":
    "Formlarla bir çizelgeleme örneği oluşturun veya mevcut şablonun kopyasını düzenleyin. Açıkça doğrulayana veya etkinleştirene kadar çalışma bu sekmede kalır.",
  "SYNTHETIC ONLY": "YALNIZCA SENTETİK VERİ",
  "Keep an exported JSON copy before reloading. Replacing the draft discards its edits and validation. Activating a copy replaces the current user input and clears earlier results and local job IDs; server jobs may continue.":
    "Yenilemeden önce JSON kopyası dışa aktarın. Taslağı değiştirmek düzenlemeleri ve doğrulamayı siler. Bir kopyayı etkinleştirmek mevcut kullanıcı girdisini değiştirir, önceki sonuçları ve yerel iş kimliklerini temizler; sunucudaki işler sürebilir.",
  "Reusable input template": "Yeniden kullanılabilir girdi şablonu",
  "Choose an executable input": "Çalıştırılabilir girdi seçin",
  "Edit a template copy": "Şablon kopyasını düzenle",
  "Start an empty input": "Boş girdiyle başla",
  "Replace the current draft and discard its edits? Original template files and the active dataset are preserved.":
    "Mevcut taslak değiştirilsin ve düzenlemeleri silinsin mi? Özgün şablon dosyaları ve etkin veri kümesi korunur.",
  "Replace draft": "Taslağı değiştir",
  "Keep current draft": "Mevcut taslağı koru",
  "Import local scheduling JSON (replaces draft)":
    "Yerel çizelgeleme JSON'u içe aktar (taslağı değiştirir)",
  "At most 256 KiB; strict UTF-8, schema 1, depth 24. Import performs preliminary checks only and sends no network request. Inspection CSV is unsupported.":
    "En fazla 256 KiB; katı UTF-8, şema 1, derinlik 24. İçe aktarma yalnızca ön kontroller yapar ve ağ isteği göndermez. İnceleme CSV'si desteklenmez.",
  "Export scheduling JSON": "Çizelgeleme JSON'u dışa aktar",
  "Production data steps": "Üretim verisi adımları",
  "Save or cancel the open form before moving to another step.":
    "Başka adıma geçmeden açık formu kaydedin veya iptal edin.",
  "{p0} preliminary issue{p1}. Frontend checks are not authoritative.":
    "{p0} ön kontrol sorunu{p1}. Arayüz kontrolleri nihai doğrulama değildir.",
  "Step {p0} of {p1}: {p2}. {p3}": "Adım {p0} / {p1}: {p2}. {p3}",
  "Product styles": "Ürün modelleri",
  "Define supported stages and exact standard worker-minutes per piece. Style definitions can be reused by many orders.":
    "Desteklenen aşamaları ve adet başına kesin standart işçi-dakika değerini tanımlayın. Ürün modeli tanımları birden fazla siparişte kullanılabilir.",
  "Production orders": "Üretim siparişleri",
  "Declare integer piece quantities, priority (1 highest), release/due dates and an ordered route through supported style stages.":
    "Tam sayı adet, öncelik (1 en yüksek), başlangıç/teslim tarihleri ve desteklenen ürün aşamalarından sıralı bir rota tanımlayın.",
  "Each line has one stage and a dedicated crew. Availability and crew size are explicit assumptions.":
    "Her hattın tek aşaması ve atanmış ekibi vardır. Kullanılabilirlik ve ekip büyüklüğü açık varsayımlardır.",
  "Line capabilities": "Hat yetkinlikleri",
  "Explicit line/style/stage qualification is required. Matching stage names alone does not create a capability.":
    "Hat/ürün modeli/aşama yetkinliği açıkça gereklidir. Yalnızca aşama adlarının eşleşmesi yetkinlik oluşturmaz.",
  "Capacity profiles": "Kapasite profilleri",
  "Assign an effective date, synthetic source and exact efficiency fraction to a line. Profile selection is explicit in the calendar; no latest-profile inference occurs.":
    "Bir hatta geçerlilik tarihi, sentetik kaynak ve kesin verimlilik oranı atayın. Profil takvimde açıkça seçilir; en güncel profil varsayılmaz.",
  "Declare dated start/end times and positioned breaks. Reuse shift definitions across distinct lines. Python checks all interval interactions.":
    "Tarihli başlangıç/bitişleri ve konumlandırılmış molaları tanımlayın. Vardiya tanımlarını farklı hatlarda kullanın. Python tüm zaman aralığı etkileşimlerini denetler.",
  "Shift assignments": "Vardiya atamaları",
  "Choose a line, declared shift and a profile belonging to that line. The profile must be effective on the explicit shift start working date.":
    "Bir hat, tanımlı vardiya ve o hatta ait profil seçin. Profil, vardiyanın başladığı çalışma tarihinde geçerli olmalıdır.",
  "Planned downtime": "Planlı duruş",
  "Stops must remain inside their assigned shift. Overlapping exclusion reasons are handled by Python's existing interval union.":
    "Duruşlar atandıkları vardiyanın içinde kalmalıdır. Çakışan dışlama nedenleri Python'un mevcut aralık birleşimiyle işlenir.",
  "Unavailable periods": "Kullanılamayan dönemler",
  "Line-wide unavailable intervals may span shifts. Give a reason and explicit timestamp bounds.":
    "Hat genelindeki kullanılamayan aralıklar birden fazla vardiyayı kapsayabilir. Neden ve açık zaman sınırları girin.",
  "Review the complete input": "Girdinin tamamını incele",
  "Preliminary checks cover syntax and references. The local Python backend owns authoritative contract and calendar validation.":
    "Ön kontroller sözdizimi ve referansları kapsar. Nihai sözleşme ve takvim doğrulamasını yerel Python sunucusu yapar.",
  "Preliminary input issues": "Girdi ön kontrol sorunları",
  "Resolve these errors before validation or export:":
    "Doğrulama veya dışa aktarma öncesi bu hataları düzeltin:",
  "Preliminary structure and references pass. Python still needs to check domain rules, break containment, calendar overlaps, profile dates and time offsets.":
    "Ön yapı ve referans kontrolleri geçti. Python'un alan kurallarını, mola kapsamını, takvim çakışmalarını, profil tarihlerini ve saat farklarını denetlemesi gerekiyor.",
  "PYTHON VALIDATED": "PYTHON İLE DOĞRULANDI",
  "NOT AUTHORITATIVELY VALIDATED": "NİHAİ DOĞRULAMA YAPILMADI",
  "Configure the local API to validate and activate. Offline import, editing and export remain available.":
    "Doğrulamak ve etkinleştirmek için yerel API'yi ayarlayın. Çevrimdışı içe aktarma, düzenleme ve dışa aktarma kullanılabilir.",
  "Accepted instance fingerprint": "Kabul edilen örnek parmak izi",
  "Validation request ID": "Doğrulama isteği kimliği",
  "Checking input…": "Girdi kontrol ediliyor…",
  "Validate with local Python": "Yerel Python ile doğrula",
  "Activate validated copy": "Doğrulanmış kopyayı etkinleştir",
  "Open production scheduling": "Üretim çizelgelemeyi aç",
  "Open capacity assessment": "Kapasite değerlendirmesini aç",
  "Active workspace: your validated synthetic copy. Further draft edits require validation and activation again.":
    "Etkin çalışma alanı: doğrulanmış sentetik kopyanız. Taslaktaki yeni düzenlemeler yeniden doğrulama ve etkinleştirme gerektirir.",
  "System-managed metadata & exact instance": "Sistemin yönettiği üst veriler ve kesin örnek",
  "Schema 1 · whole-stage-minute-v1 · one-minute allocation · piece output · synthetic profile evidence. Internal IDs are generated for profiles, qualifications, assignments and stops. No exporter, benchmark, session or credential fields are included.":
    "Şema 1 · whole-stage-minute-v1 · bir dakikalık atama · adet çıktısı · sentetik profil kanıtı. Profil, yetkinlik, atama ve duruş kimlikleri sistem tarafından üretilir. Dışa aktarıcı, kıyaslama, oturum veya kimlik bilgisi alanları içermez.",
  "Exact synthetic scheduling instance": "Kesin sentetik çizelgeleme örneği",
  "Previous step": "Önceki adım",
  "Next step": "Sonraki adım",
  "No resources loaded": "Kaynak yüklenmedi",
  "Choose a bundled planning dataset.": "Paketlenmiş bir planlama veri kümesi seçin.",
  "Crews and efficiency are declared synthetic planning assumptions. Available time is a capacity input; allocated work appears only in an explicitly loaded verified schedule.":
    "Ekipler ve verimlilik, tanımlı sentetik planlama varsayımlarıdır. Kullanılabilir süre kapasite girdisidir; atanmış iş yalnızca açıkça yüklenen doğrulanmış çizelgede görünür.",
  "declared workers": "tanımlı işçi",
  "Line–style capabilities": "Hat–ürün modeli yetkinlikleri",
  "assumed efficiency": "varsayılan verimlilik",
  "{p0} · effective {p1}": "{p0} · geçerlilik: {p1}",
  Assignments: "Atamalar",
  "Profile: {p0}": "Profil: {p0}",
  "No production lines": "Üretim hattı yok",
  "No lines are declared in this input.": "Bu girdide hat tanımlanmadı.",
  "Shift calendar": "Vardiya takvimi",
  "Input intervals with explicit timezone offsets; no browser timezone conversion":
    "Açık saat farklarıyla girdi aralıkları; tarayıcı saat dilimine dönüştürülmez",
  "Shift calendar scrollable table": "Yatay kaydırılabilir vardiya takvimi tablosu",
  Start: "Başlangıç",
  End: "Bitiş",
  "Declared breaks": "Tanımlı molalar",
  "References a specific line–shift assignment": "Belirli bir hat–vardiya atamasına bağlıdır",
  "No planned downtime": "Planlı duruş yok",
  "No downtime intervals are declared.": "Duruş aralığı tanımlanmadı.",
  "Line unavailability": "Hat kullanılamazlığı",
  "Input restrictions, not measured production losses":
    "Girdi kısıtlarıdır; ölçülen üretim kaybı değildir",
  "No unavailable periods": "Kullanılamayan dönem yok",
  "No additional unavailable intervals are declared.": "Ek kullanılamayan aralık tanımlanmadı.",
  "No declared choices": "Tanımlı seçenek yok",
  "Changes are hypothetical capacity assumptions. The original baseline stays immutable. Use existing lines, profiles, capabilities and declared shifts only. Python validates the complete atomic transaction; no dangling-reference cleanup is inferred.":
    "Değişiklikler varsayımsal kapasite varsayımlarıdır. Özgün referans sabit kalır. Yalnızca mevcut hat, profil, yetkinlik ve tanımlı vardiyaları kullanın. Python işlemin tamamını atomik olarak doğrular; boşa düşen referanslar otomatik temizlenmez.",
  "Run reference scheduling first to obtain this baseline’s verified fingerprint.":
    "Bu referansın doğrulanmış parmak izini almak için önce referans çizelgelemeyi çalıştırın.",
  "1 · Build ordered changes": "1 · Sıralı değişiklikleri oluştur",
  "Immutable baseline": "Değişmez referans",
  "Supported capacity change": "Desteklenen kapasite değişikliği",
  "Change operation": "Değişiklik işlemi",
  "Add change to review": "Değişikliği incelemeye ekle",
  "Ordered list · maximum 64 edits per HTTP request":
    "Sıralı liste · HTTP isteği başına en fazla 64 düzenleme",
  "Move change {p0} up": "{p0}. değişikliği yukarı taşı",
  "Remove change {p0}": "{p0}. değişikliği kaldır",
  "No changes added. An explicit empty/no-op scenario is valid.":
    "Değişiklik eklenmedi. Açıkça boş veya etkisiz senaryo geçerlidir.",
  "2 · Declare provenance & execution": "2 · Köken ve çalıştırmayı tanımla",
  "Scenario provenance": "Senaryo kökeni",
  "Scenario label": "Senaryo etiketi",
  "Synthetic source ID": "Sentetik kaynak kimliği",
  "Assumption (single canonical entry)": "Varsayım (tek, kurallı kayıt)",
  "Request bounded CP-SAT comparison job": "Sınırlı CP-SAT karşılaştırma işi iste",
  "Wall seconds per phase (0–1)": "Faz başına gerçek süre (saniye, 0–1)",
  "Deterministic units per phase (0–1)": "Faz başına deterministik birim (0–1)",
  "Explicit seed 42, worker 1, benchmark mode. Zero is an intentional no-search diagnostic and can produce UNKNOWN with verified greedy fallback. Budgets are never silently clamped.":
    "Açık tohum 42, iş parçacığı 1, kıyaslama modu. Sıfır, bilinçli bir aramasız tanı ayarıdır; doğrulanmış açgözlü yönteme dönüşle UNKNOWN üretebilir. Bütçeler sessizce sınırlandırılmaz.",
  "Review exact specification": "Kesin değişiklik tanımını incele",
  "3 · Review before execution": "3 · Çalıştırmadan önce incele",
  "Exact numeric tokens · {p0}": "Kesin sayısal değerler · {p0}",
  "bounded CP-SAT job": "sınırlı CP-SAT işi",
  "synchronous greedy comparison": "eşzamanlı açgözlü yöntem karşılaştırması",
  "Submit reviewed CP-SAT comparison job": "İncelenen CP-SAT karşılaştırma işini gönder",
  "Run reviewed greedy comparison": "İncelenen açgözlü karşılaştırmayı çalıştır",
  "The backend validates this exact request atomically. Rejected requests are never retried with altered assumptions. A lost POST response may leave an admitted job; do not resubmit automatically.":
    "Sunucu bu kesin isteği atomik olarak doğrular. Reddedilen istekler değiştirilmiş varsayımlarla yeniden denenmez. Kaybolan POST yanıtına rağmen iş kabul edilmiş olabilir; otomatik yeniden göndermeyin.",
  "Actual API comparison": "Gerçek API karşılaştırması",
  "Request ID:": "İstek kimliği:",
  "Frozen scheduling input": "Sabit çizelgeleme girdisi",
  Instance: "Örnek",
  "Capacity-only input": "Yalnızca kapasite girdisi",
  Envelope: "İstek sınırı",
  "{p0} orders · {p1} operations / maximum 32 orders, 96 operations":
    "{p0} sipariş · {p1} operasyon / en fazla 32 sipariş, 96 operasyon",
  "Horizon / source offsets": "Planlama ufku / kaynak saat farkları",
  "{p0} → {p1}": "{p0} → {p1}",
  "Not a scheduling contract": "Çizelgeleme sözleşmesi değil",
  Source: "Kaynak",
  "Inspect orders & stages": "Siparişleri ve aşamaları incele",
  "Inspect resources & calendar": "Kaynakları ve takvimi incele",
  "Frozen policy & complete input": "Sabit politika ve girdinin tamamı",
  "whole-stage-minute-v1: full-batch, nonpreemptive stages, one compatible line and one working fragment; precedence and finite line reservations. Priority 1 is highest. No splitting, shared crews, materials, setups, initial WIP or ML capacity.":
    "whole-stage-minute-v1: tam parti, bölünemeyen aşamalar, tek uyumlu hat ve tek çalışma aralığı; öncelik ilişkileri ve sonlu hat rezervasyonları. Öncelik 1 en yüksektir. Bölme, ortak ekip, malzeme, hazırlık, başlangıç yarı mamulü veya ML kapasitesi yoktur.",
  "Complete frozen scheduling input": "Sabit çizelgeleme girdisinin tamamı",
  "Run reference again": "Referansı yeniden çalıştır",
  "Run reference scheduling": "Referans çizelgelemeyi çalıştır",
  "Submit bounded CP-SAT job": "Sınırlı CP-SAT işi gönder",
  "Build a what-if scenario →": "Varsayımsal senaryo oluştur →",
  "Submitting creates server work. POST is not idempotent: repeated submissions can create duplicates. Leaving a page stops polling; changing dataset/session clears local tracking and results. Jobs may continue on the server. Copy the job ID first; only explicit Cancel requests termination.":
    "Gönderim sunucuda iş oluşturur. POST tekrarı aynı sonucu garanti etmez: yinelenen gönderimler mükerrer iş oluşturabilir. Sayfadan ayrılmak sorgulamayı durdurur; veri kümesi/oturum değişikliği yerel takibi ve sonuçları temizler. İşler sunucuda sürebilir. Önce iş kimliğini kopyalayın; yalnızca açık İptal isteği sonlandırma talep eder.",
  "Actual API response": "Gerçek API yanıtı",
  "Dispatch request ID:": "Çizelgeleme isteği kimliği:",
  "Instance fingerprint:": "Örnek parmak izi:",
  "No reference schedule loaded": "Referans çizelge yüklenmedi",
  "Select Competing orders, Capacity what-if, Routing trade-off or Parallel production, connect the local API and run the reference scheduler.":
    "Çakışan siparişler, Kapasite senaryosu, Rota ödünleşimi veya Paralel üretim veri kümesini seçin, yerel API'ye bağlanın ve referans çizelgeleyiciyi çalıştırın.",
  "Local API session": "Yerel API oturumu",
  "Actual responses from the configured loopback backend":
    "Ayarlanan geri döngü sunucusundan gerçek yanıtlar",
  "Data mode": "Veri modu",
  "Explicit fixture preview": "Açık örnek veri önizlemesi",
  "Local API": "Yerel API",
  "Not connected": "Bağlı değil",
  "Health response": "Sağlık kontrolü yanıtı",
  "{p0} · last successful check": "{p0} · son başarılı kontrol",
  "Not checked": "Kontrol edilmedi",
  "API version": "API sürümü",
  "Not loaded": "Yüklenmedi",
  "Credential storage": "Kimlik bilgisi saklama",
  "Tab memory only": "Yalnızca sekme belleği",
  "Checking the backend and loading capacity…": "Sunucu kontrol ediliyor ve kapasite yükleniyor…",
  "Clear session & use fixture preview": "Oturumu temizle ve örnek önizlemeye geç",
  "Refresh capacity report": "Kapasite raporunu yenile",
  "Workspace boundaries": "Çalışma alanının sınırları",
  "Planning & capacity": "Planlama ve kapasite",
  "Existing schedule inspection": "Mevcut çizelge incelemesi",
  "Explicit read-only verification; no solver run":
    "Açık, salt okunur doğrulama; çözücü çalıştırılmaz",
  "Productivity prediction": "Verimlilik tahmini",
  "Interactive scheduling & what-if": "Etkileşimli çizelgeleme ve senaryolar",
  "Available in dedicated scheduling, scenarios and jobs views":
    "Çizelgeleme, senaryo ve iş sayfalarında kullanılabilir",
  "Reported capabilities": "Bildirilen yetenekler",
  "Loaded from GET /api/v1/capabilities": "GET /api/v1/capabilities yanıtından yüklendi",
  "Policy versions": "Politika sürümleri",
  "Backend operations": "Sunucu işlemleri",
  "Synchronous scheduling methods": "Eşzamanlı çizelgeleme yöntemleri",
  "Prediction availability": "Tahmin kullanılabilirliği",
  "Synchronous execution limits": "Eşzamanlı çalıştırma sınırları",
  "Exact integer values returned by the current backend":
    "Mevcut sunucunun döndürdüğü kesin tam sayı değerleri",
  "Bounded job limits": "Sınırlı iş bütçeleri",
  "Backend limitations": "Sunucu sınırlamaları",
  "Backend capabilities": "Sunucu yetenekleri",
  "Capabilities not loaded": "Yetenekler yüklenmedi",
  "Configure a local API session to inspect the actual server limits and supported operations.":
    "Gerçek sunucu sınırlarını ve desteklenen işlemleri incelemek için yerel API oturumu ayarlayın.",
  "The local backend is unreachable. Check the server and configured origin.":
    "Yerel sunucuya ulaşılamıyor. Sunucuyu ve ayarlanan adresi kontrol edin.",
  "The local session was rejected. Check the Bearer token and allowed origin.":
    "Yerel oturum reddedildi. Bearer anahtarını ve izin verilen adresi kontrol edin.",
  "The backend rejected this input. No capacity or schedule result was accepted.":
    "Sunucu bu girdiyi reddetti. Kapasite veya çizelgeleme sonucu kabul edilmedi.",
  "The local execution slots are busy. Wait briefly and retry.":
    "Yerel çalıştırma yuvaları dolu. Kısa süre bekleyip yeniden deneyin.",
  "The bounded request reached its deadline. Retry when the local backend is ready.":
    "Sınırlı istek süre sınırına ulaştı. Yerel sunucu hazır olduğunda yeniden deneyin.",
  "The backend response does not match the supported API contract.":
    "Sunucu yanıtı desteklenen API sözleşmesiyle eşleşmiyor.",
  "The backend could not complete this request. No replacement result was invented.":
    "Sunucu bu isteği tamamlayamadı. Yerine başka bir sonuç üretilmedi.",
  "The local request was cancelled.": "Yerel istek iptal edildi.",
  "The job is missing. Its record may have expired or the local server may have restarted.":
    "İş bulunamadı. Kayıt süresi dolmuş veya yerel sunucu yeniden başlamış olabilir.",
  "The server's volatile result retention has expired. No result is available.":
    "Sunucudaki geçici sonuç saklama süresi doldu. Sonuç mevcut değil.",
  "The job result is unavailable in its current state. Inspect its actual status.":
    "İş sonucu mevcut durumda kullanılamıyor. Gerçek durumunu inceleyin.",
  "A break lies outside its shift. Check Shifts & breaks.":
    "Mola vardiyasının dışında kalıyor. Vardiyalar ve molaları kontrol edin.",
  "Breaks overlap. Check Shifts & breaks.":
    "Molalar çakışıyor. Vardiyalar ve molaları kontrol edin.",
  "Assignments overlap on the same line. Check the production calendar.":
    "Aynı hattaki atamalar çakışıyor. Üretim takvimini kontrol edin.",
  "Downtime lies outside its assigned shift. Check the production calendar.":
    "Duruş, atandığı vardiyanın dışında kalıyor. Üretim takvimini kontrol edin.",
  "A capacity profile is not effective at shift start. Check profile dates.":
    "Kapasite profili vardiya başlangıcında geçerli değil. Profil tarihlerini kontrol edin.",
  "The selected profile belongs to another line. Check assignments.":
    "Seçili profil başka hatta ait. Atamaları kontrol edin.",
  "An assigned shift starts on an undeclared working date. Add that date explicitly.":
    "Atanan vardiya tanımlanmamış bir çalışma tarihinde başlıyor. Bu tarihi açıkça ekleyin.",
  "A shift start uses a different offset from the fixed calendar offset.":
    "Vardiya başlangıcı sabit takvimden farklı bir saat farkı kullanıyor.",
  "All horizon, shift, break and stop boundaries must align to whole minutes.":
    "Planlama ufku, vardiya, mola ve duruş sınırları tam dakikalara hizalanmalıdır.",
  "An interval ends before it starts. Check its explicit endpoints.":
    "Zaman aralığı başlamadan bitiyor. Açık başlangıç ve bitişleri kontrol edin.",
  "A shift must end after it starts.": "Vardiya başladığı zamandan sonra bitmelidir.",
  "The scheduling horizon must end after it starts.":
    "Planlama ufku başladığı zamandan sonra bitmelidir.",
  "A required entity reference is missing. Review orders, resources and calendar.":
    "Gerekli bir kayıt referansı eksik. Siparişleri, kaynakları ve takvimi inceleyin.",
  "An identifier is repeated. Review the affected entity lists.":
    "Bir kimlik tekrarlanıyor. İlgili kayıt listelerini inceleyin.",
  "An order release date follows its due date.":
    "Sipariş başlangıç tarihi teslim tarihinden sonra.",
  "A qualification must match both its line stage and a supported style stage.":
    "Yetkinlik hem hat aşamasıyla hem de desteklenen ürün modeli aşamasıyla eşleşmelidir.",
  COMPLETED: "TAMAMLANDI",
  BETTER: "DAHA İYİ",
  WORSE: "DAHA KÖTÜ",
  "Standard worker-minutes per piece": "Adet başına standart işçi-dakika",
  "{p0}: {p1}": "{p0}: {p1}",
  "Capacity foundation": "Kapasite temeli",
  "Competing orders": "Çakışan siparişler",
  "Capacity what-if": "Kapasite senaryosu",
  "Routing trade-off": "Rota ödünleşimi",
  "Parallel production": "Paralel üretim",
  INVALID: "GEÇERSİZ",
  Jan: "Oca",
  Feb: "Şub",
  Mar: "Mar",
  Apr: "Nis",
  May: "May",
  Jun: "Haz",
  Jul: "Tem",
  Aug: "Ağu",
  Sep: "Eyl",
  Oct: "Eki",
  Nov: "Kas",
  Dec: "Ara",
  "{p0} {p1} {p2}": "{p0} {p1} {p2}",
  "{p0}, {p1} {p2}": "{p0}, {p1} {p2}",
  "Declared break": "Tanımlı mola",
  EXPIRED: "SÜRESİ DOLDU",
  "The loaded data does not match the supported synthetic contract.":
    "Yüklenen veri desteklenen sentetik sözleşmeyle eşleşmiyor.",
  "Completed orders": "Tamamlanan siparişler",
  "Incomplete orders": "Tamamlanmamış siparişler",
  "Partially allocated orders": "Kısmen atanan siparişler",
  "Allocated operations": "Atanan operasyonlar",
  "Unscheduled operations": "Çizelgelenmemiş operasyonlar",
  "Allocated stage units": "Atanan aşama adetleri",
  "On-time completed orders": "Zamanında tamamlanan siparişler",
  "Late completed orders": "Geç tamamlanan siparişler",
  "Completed-order tardiness": "Tamamlanan siparişlerin gecikmesi",
  "Priority-weighted tardiness": "Öncelik ağırlıklı gecikme",
  Makespan: "Toplam tamamlanma süresi",
  "Available line time": "Kullanılabilir hat süresi",
  "Occupied line time": "Kullanılan hat süresi",
  "Consumed crew time": "Tüketilen ekip süresi",
  "Unused crew time": "Kullanılmayan ekip süresi",
  "Available standard capacity": "Kullanılabilir standart kapasite",
  "Consumed standard capacity": "Tüketilen standart kapasite",
  "Unused standard capacity": "Kullanılmayan standart kapasite",
  "Standard capacity utilization": "Standart kapasite kullanım oranı",
  "Reserved rounding slack": "Ayrılan yuvarlama payı",
  TIE: "EŞİT",
  DEFINED: "TANIMLI",
  QUEUED: "KUYRUKTA",
  RUNNING: "ÇALIŞIYOR",
  SUCCEEDED: "BAŞARILI",
  FAILED: "BAŞARISIZ",
  CANCELLED: "İPTAL EDİLDİ",
  PARTIAL: "KISMİ",
  TERMINAL: "SON DURUM",
  "Random Forest": "Random Forest",
  "Grouped Mean baseline": "Grouped Mean baseline",
  "RF Physics": "RF Physics",
  "History Boost": "History Boost",
  "History counts must be whole numbers from 0 to 7, with uncensored count no larger than total.":
    "Geçmiş sayıları 0–7 arasında tam sayı olmalı; sansürlenmemiş sayı toplamı aşmamalıdır.",
  "Mean and standard deviation require at least two uncensored mature reports; otherwise leave both empty.":
    "Ortalama ve standart sapma için en az iki sansürlenmemiş olgun rapor gerekir; aksi durumda ikisini de boş bırakın.",
  "History age must describe an existing mature report, from 0 to 8760 hours.":
    "Geçmiş yaşı mevcut bir olgun raporu tanımlamalı ve 0–8760 saat arasında olmalıdır.",
  "Planned workers": "Planlanan işçi sayısı",
  "Dedicated crew headcount; 0 means undefined planned capacity.":
    "Atanmış ekip sayısı; 0, planlı kapasitenin tanımsız olması demektir.",
  "Skill level": "Beceri düzeyi",
  "Declared crew qualification level, from 1 to 5.": "Tanımlı ekip yetkinlik düzeyi: 1–5.",
  "Product complexity": "Ürün karmaşıklığı",
  "Declared style complexity, from 1 to 5.": "Tanımlı ürün modeli karmaşıklığı: 1–5.",
  "Declared labor standard per completed good piece; at most 2 decimals.":
    "Tamamlanan sağlam adet başına tanımlı işçilik standardı; en fazla 2 ondalık basamak.",
  "Planned available time (minutes)": "Planlanan kullanılabilir süre (dakika)",
  "Elapsed time after the union of breaks, downtime and machine stops. Exclude stops once.":
    "Mola, duruş ve makine kesintilerinin birleşimi çıkarıldıktan sonraki süre. Kesintileri yalnızca bir kez çıkarın.",
  "Planned downtime (minutes)": "Planlı duruş (dakika)",
  "Already accounted for in available time; do not subtract it again.":
    "Kullanılabilir sürede zaten hesaba katılmıştır; yeniden çıkarmayın.",
  "Opening WIP (pieces)": "Başlangıç yarı mamulü (adet)",
  "Pieces already waiting at this production stage before shift start.":
    "Vardiya başlamadan bu üretim aşamasında bekleyen adetler.",
  "Planned release (pieces)": "Planlanan giriş (adet)",
  "Pieces planned to enter this stage; opening WIP + release must equal order quantity.":
    "Bu aşamaya girmesi planlanan adet; başlangıç yarı mamulü + giriş, sipariş miktarına eşit olmalıdır.",
  "Order quantity (pieces)": "Sipariş miktarı (adet)",
  "Total work declared for this order-stage observation.":
    "Bu sipariş-aşama gözlemi için tanımlanan toplam iş.",
  "{p0} requires a {p1} from {p2} to {p3}.": "{p0} için {p2}–{p3} aralığında {p1} gerekir.",
  "whole number": "tam sayı",
  "number with at most two decimals": "en fazla iki ondalık basamaklı sayı",
  "Opening WIP plus planned release must equal order quantity.":
    "Başlangıç yarı mamulü ile planlanan girişin toplamı sipariş miktarına eşit olmalıdır.",
  "Available time plus planned downtime must fit within a 480 minute shift.":
    "Kullanılabilir süre ve planlı duruş toplamı 480 dakikalık vardiyaya sığmalıdır.",
  ABSTAIN: "TAHMİN ÜRETİLMEDİ",
  "Enter nonblank text without surrounding spaces or control characters.":
    "Başında/sonunda boşluk veya kontrol karakteri olmayan, boş olmayan metin girin.",
  "Unsupported version, unit or synthetic provenance.":
    "Desteklenmeyen sürüm, birim veya sentetik veri kökeni.",
  "Choose a supported value.": "Desteklenen bir değer seçin.",
  "Use an exact JSON numeric token.": "Kesin bir JSON sayısal değeri kullanın.",
  "Choose an integer fixed offset between -1439 and 1439 minutes.":
    "-1439 ile 1439 dakika arasında tam sayı sabit saat farkı seçin.",
  "Enter an exact nonnegative number within the API numeric bounds.":
    "API sayısal sınırları içinde kesin, negatif olmayan sayı girin.",
  "Enter a whole integer count.": "Tam sayı adet girin.",
  "Enter a value greater than zero.": "Sıfırdan büyük bir değer girin.",
  "Efficiency must be between zero and one; it is never clamped.":
    "Verimlilik sıfır ile bir arasında olmalıdır; otomatik sınırlandırılmaz.",
  "Enter a valid YYYY-MM-DD date.": "YYYY-MM-DD biçiminde geçerli tarih girin.",
  "Use a valid minute-aligned timestamp with seconds and explicit offset.":
    "Saniye ve açık saat farkı içeren, tam dakikaya hizalı geçerli zaman damgası kullanın.",
  "Expected a list.": "Liste bekleniyor.",
  "Add at least one item.": "En az bir öğe ekleyin.",
  "Expected a record.": "Kayıt bekleniyor.",
  "Unsupported fields; only scheduling instance data is accepted.":
    "Desteklenmeyen alanlar; yalnızca çizelgeleme örneği verileri kabul edilir.",
  "Required field is missing.": "Gerekli alan eksik.",
  "The complete request exceeds the API file/body size limit; nothing was truncated.":
    "İsteğin tamamı API dosya/gövde boyutu sınırını aşıyor; hiçbir şey kesilmedi.",
  "Input exceeds the API nesting or node limit.":
    "Girdi, API iç içe geçme veya düğüm sınırını aşıyor.",
  "Input contains oversized or invalid Unicode text.":
    "Girdi aşırı uzun veya geçersiz Unicode metni içeriyor.",
  "Input exceeds the API numeric limit.": "Girdi API sayısal sınırını aşıyor.",
  "A list exceeds the API collection limit.": "Liste, API koleksiyon sınırını aşıyor.",
  "A record exceeds the API collection limit.": "Kayıt, API koleksiyon sınırını aşıyor.",
  "Input exceeds the API limit of at most 32 orders / 96 operations; nothing was truncated.":
    "Girdi en fazla 32 sipariş / 96 operasyon API sınırını aşıyor; hiçbir şey kesilmedi.",
  "Malformed or unsupported scheduling input.": "Bozuk veya desteklenmeyen çizelgeleme girdisi.",
  Policy: "Politika",
  "Only schema 1 and one-minute allocation are supported.":
    "Yalnızca şema 1 ve bir dakikalık atama desteklenir.",
  Lines: "Hatlar",
  Profiles: "Profiller",
  Capabilities: "Yetkinlikler",
  Downtime: "Duruş",
  "Duplicate identifiers must be resolved.": "Yinelenen kimlikler düzeltilmelidir.",
  "Missing or conflicting reference; edit the affected record.":
    "Eksik veya çelişen referans; ilgili kaydı düzenleyin.",
  "Orders / style stages": "Siparişler / ürün aşamaları",
  "Orders / dates": "Siparişler / tarihler",
  "Release cannot follow due date.": "Başlangıç teslim tarihinden sonra olamaz.",
  "Orders / stages": "Siparişler / aşamalar",
  "Repeated stages are unsupported.": "Tekrarlanan aşamalar desteklenmez.",
  "Styles / standards": "Ürün modelleri / standartlar",
  "Each stage needs exactly one standard.": "Her aşama için tam bir standart gerekir.",
  "Profiles / line": "Profiller / hat",
  "Duplicate line/style/stage capability.": "Yinelenen hat/ürün modeli/aşama yetkinliği.",
  "Capabilities / line and style stage": "Yetkinlikler / hat ve ürün aşaması",
  "Assignments / line, shift and profile": "Atamalar / hat, vardiya ve profil",
  "Downtime / assignment": "Duruş / atama",
  "Unavailability / line": "Kullanılamazlık / hat",
  "Calendar / working dates": "Takvim / çalışma tarihleri",
  "Remove duplicate working dates.": "Yinelenen çalışma tarihlerini kaldırın.",
  "Import requires bounded, unique-key UTF-8 scheduling JSON. CSV and inspection exports are unsupported.":
    "İçe aktarma; boyutu sınırlı, benzersiz anahtarlı UTF-8 çizelgeleme JSON'u gerektirir. CSV ve inceleme dışa aktarımları desteklenmez.",
  "File exceeds the 256 KiB limit; nothing was read or uploaded.":
    "Dosya 256 KiB sınırını aşıyor; hiçbir şey okunmadı veya yüklenmedi.",
  "Cannot read a strict UTF-8 scheduling JSON file.":
    "Katı UTF-8 çizelgeleme JSON dosyası okunamıyor.",
  "Resolve preliminary input errors before exporting.":
    "Dışa aktarmadan önce ön kontrol hatalarını düzeltin.",
  "{p0}\n": "{p0}",
  "Validation identity does not match this draft.": "Doğrulama kimliği bu taslakla eşleşmiyor.",
  "My synthetic production input": "Sentetik üretim girdim",
  "Local user workspace · exact serialized input (LF)":
    "Yerel kullanıcı çalışma alanı · kesin serileştirilmiş girdi (LF)",
  "Hypothetical capacity change": "Varsayımsal kapasite değişikliği",
  "Conditional synthetic planning only. Declared crews are assumed qualified; efficiency is hypothetical, not observed productivity.":
    "Yalnızca koşullu sentetik planlama. Tanımlı ekiplerin yetkin olduğu varsayılır; verimlilik varsayımsaldır, gözlemlenmiş üretkenlik değildir.",
  "{p0} must be nonblank canonical text without control characters.":
    "{p0}, kontrol karakteri içermeyen, boş olmayan kurallı metin olmalıdır.",
  "Enter an exact nonnegative numeric value; it will not be rounded or clamped.":
    "Kesin, negatif olmayan sayısal değer girin; yuvarlanmaz veya sınırlandırılmaz.",
  "Fractional values must be between zero and one, with a supported exponent.":
    "Kesirli değerler sıfır ile bir arasında ve desteklenen üslü gösterimde olmalıdır.",
  "The HTTP envelope permits at most 64 ordered changes.":
    "HTTP isteği en fazla 64 sıralı değişikliğe izin verir.",
  "This entity field already has an edit. Remove that change first; repeated lifecycle edits conflict.":
    "Bu kayıt alanında zaten düzenleme var. Önce onu kaldırın; tekrarlanan yaşam döngüsü düzenlemeleri çakışır.",
  "Select an existing baseline reference.": "Mevcut bir referans kaydı seçin.",
  "Assignment ID already exists.": "Atama kimliği zaten var.",
  "Downtime ID already exists.": "Duruş kimliği zaten var.",
  "Downtime requires explicit offset timestamps and an end after its start.":
    "Duruş için açık saat farkı içeren zaman damgaları ve başlangıçtan sonra bitiş gerekir.",
  "This M02 input is a capacity scenario, not an executable scheduling instance. Select a frozen M03/M04 instance.":
    "Bu girdi bir kapasite senaryosudur, çalıştırılabilir çizelgeleme örneği değildir. Bir çizelgeleme veya senaryo örneği seçin.",
  "Unsupported HTTP instance: {p0} orders / {p1} operations exceed the published envelope (at most 32 / 96). Inputs are never truncated.":
    "Desteklenmeyen HTTP örneği: {p0} sipariş / {p1} operasyon, yayımlanan sınırı aşıyor (en fazla 32 / 96). Girdiler kesilmez.",
  "Run and verify reference scheduling for this exact baseline first.":
    "Önce tam bu referans için çizelgelemeyi çalıştırıp doğrulayın.",
  "Resolve conflicting edits or the 64-change envelope first.":
    "Önce çakışan düzenlemeleri veya 64 değişiklik sınırını düzeltin.",
  Label: "Etiket",
  "Source ID": "Kaynak kimliği",
  Assumptions: "Varsayımlar",
  "Running reference scheduling": "Referans çizelgeleme çalışıyor",
  "Comparing the reviewed scenario": "İncelenen senaryo karşılaştırılıyor",
  "Submitting a bounded job — POST is not idempotent":
    "Sınırlı iş gönderiliyor — POST tekrarı mükerrer iş oluşturabilir",
  "Dataset or session changed. Validate the draft again; earlier server jobs may continue.":
    "Veri kümesi veya oturum değişti. Taslağı yeniden doğrulayın; önceki sunucu işleri sürebilir.",
  "Resolve preliminary errors before backend validation.":
    "Sunucu doğrulamasından önce ön kontrol hatalarını düzeltin.",
  "Python accepted the complete synthetic input. Scheduling feasibility has not been assessed.":
    "Python sentetik girdinin tamamını kabul etti. Çizelgeleme uygunluğu değerlendirilmedi.",
  "Validated copy activated. Open Production scheduling to run the reference.":
    "Doğrulanmış kopya etkinleştirildi. Referansı çalıştırmak için Üretim çizelgeleme sayfasını açın.",
  "Unable to activate this draft.": "Bu taslak etkinleştirilemedi.",
  "Verified production schedule": "Doğrulanmış üretim çizelgesi",
  "reported line": "bildirilen hat",
  "Producer & solver evidence": "Yöntem ve çözücü kanıtı",
  Abstained: "Tahmin üretilmedi",
  "Supported stage": "Desteklenen aşama",
  "Break start (with offset)": "Mola başlangıcı (saat farkıyla)",
  "Break end (with offset)": "Mola bitişi (saat farkıyla)",
  "Style name / ID": "Ürün modeli adı / kimliği",
  "Order ID": "Sipariş kimliği",
  "Product style": "Ürün modeli",
  "Priority (1 is highest)": "Öncelik (1 en yüksek)",
  "Release date": "Başlangıç tarihi",
  "Line name / ID": "Hat adı / kimliği",
  "Line stage": "Hat aşaması",
  "Dedicated worker count": "Atanmış işçi sayısı",
  "A whole number; zero is allowed and means zero labor capacity.":
    "Tam sayı; sıfır kullanılabilir ve sıfır işçilik kapasitesi anlamına gelir.",
  "Line availability": "Hat kullanılabilirliği",
  Available: "Kullanılabilir",
  Unavailable: "Kullanılamaz",
  "Profile effective date": "Profil geçerlilik tarihi",
  "Assumed efficiency (0–1)": "Varsayılan verimlilik (0–1)",
  "Explicit synthetic capacity derating, not observed productivity or an ML prediction.":
    "Açık sentetik kapasite azaltma varsayımıdır; gözlemlenen üretkenlik veya ML tahmini değildir.",
  "Synthetic assumption source": "Sentetik varsayım kaynağı",
  "Synthetic evidence reference (optional)": "Sentetik kanıt referansı (isteğe bağlı)",
  "A text reference only; no URL or file is opened.":
    "Yalnızca metin referansı; bağlantı veya dosya açılmaz.",
  "Qualified product style": "Yetkin olunan ürün modeli",
  "Qualified stage": "Yetkin olunan aşama",
  "Synthetic crew qualification basis": "Sentetik ekip yetkinliğinin dayanağı",
  "Explain why this dedicated crew is assumed qualified for this exact style and stage.":
    "Atanmış bu ekibin tam bu ürün modeli ve aşamada neden yetkin varsayıldığını açıklayın.",
  "Shift name / ID": "Vardiya adı / kimliği",
  "Shift start (with offset)": "Vardiya başlangıcı (saat farkıyla)",
  "Shift end (with offset)": "Vardiya bitişi (saat farkıyla)",
  "Declared shift": "Tanımlı vardiya",
  "Capacity profile": "Kapasite profili",
  "Affected assignment": "Etkilenen atama",
  "Downtime start (with offset)": "Duruş başlangıcı (saat farkıyla)",
  "Downtime end (with offset)": "Duruş bitişi (saat farkıyla)",
  "Downtime reason": "Duruş nedeni",
  "Unavailable start (with offset)": "Kullanılamazlık başlangıcı (saat farkıyla)",
  "Unavailable end (with offset)": "Kullanılamazlık bitişi (saat farkıyla)",
  "Unavailability reason": "Kullanılamazlık nedeni",
  "Check the required fields and exact numeric syntax. No values were rounded or saved.":
    "Gerekli alanları ve kesin sayısal sözdizimini kontrol edin. Hiçbir değer yuvarlanmadı veya kaydedilmedi.",
  "This identifier is already used. Choose a unique name / ID.":
    "Bu kimlik zaten kullanılıyor. Benzersiz ad / kimlik seçin.",
  "Record removed. Check references in Review; dependent records are retained for explicit repair.":
    "Kayıt kaldırıldı. İnceleme adımında referansları kontrol edin; bağlı kayıtlar açıkça düzeltilmeniz için korunur.",
  "{p0} pieces · {p1}": "{p0} adet · {p1}",
  "{p0} · {p1} workers": "{p0} · {p1} işçi",
  "{p0} · {p1} · efficiency {p2}": "{p0} · {p1} · verimlilik {p2}",
  "{p0} · {p1} · efficiency {p2} · {p3}": "{p0} · {p1} · verimlilik {p2} · {p3}",
  "AI Predictions": "Yapay zekâ tahminleri",
  "Run experimental synthetic ML models, compare a baseline and explore planned conditions.":
    "Deneysel sentetik makine öğrenmesi modellerini çalıştırın, referansla karşılaştırın ve planlanan koşulları keşfedin.",
  "Production data": "Üretim verileri",
  "Build, validate and exchange your own synthetic production inputs.":
    "Kendi sentetik üretim girdilerinizi oluşturun, doğrulayın ve aktarın.",
  Overview: "Genel bakış",
  "A clear view of your planning inputs and available capacity.":
    "Planlama girdilerinizi ve kullanılabilir kapasiteyi birlikte inceleyin.",
  "Inspect demand, delivery dates and declared production routes.":
    "Talebi, teslim tarihlerini ve tanımlı üretim rotalarını inceleyin.",
  "Production resources": "Üretim kaynakları",
  "Understand the people, lines and time behind each capacity slot.":
    "Her kapasite diliminin arkasındaki iş gücünü, hatları ve süreyi inceleyin.",
  Capacity: "Kapasite",
  "Production scheduling": "Üretim çizelgeleme",
  "Run the reference scheduler and inspect verified production allocations.":
    "Referans çizelgeleyiciyi çalıştırın ve doğrulanmış üretim atamalarını inceleyin.",
  "What-if scenarios": "Varsayımsal senaryolar",
  "Review explicit capacity assumptions and compare verified same-demand results.":
    "Açık kapasite varsayımlarını inceleyin ve aynı talep için doğrulanmış sonuçları karşılaştırın.",
  "Optimization jobs": "Optimizasyon işleri",
  "Track bounded jobs, cancel explicitly and inspect verified solver evidence.":
    "Sınırlı işleri izleyin, açıkça iptal edin ve doğrulanmış çözücü kanıtlarını inceleyin.",
  "API & system": "API ve sistem",
  "Inspect the local connection, capabilities and execution boundaries.":
    "Yerel bağlantıyı, yetenekleri ve çalıştırma sınırlarını inceleyin.",
  "Connecting / loading": "Bağlanıyor / yükleniyor",
  "Connection needs attention": "Bağlantı kontrol edilmeli",
  "Local API response loaded": "Yerel API yanıtı yüklendi",
  "API disconnected": "API bağlı değil",
  "Local tracking paused at its 60-request / 90-second budget. Server work may continue; resume explicitly.":
    "Yerel takip, 60 istek / 90 saniye bütçesinde durakladı. Sunucudaki iş sürebilir; takibi açıkça sürdürün.",
  "Tracking stopped on the server’s terminal status. SUCCEEDED means a verified report is available, not that CP-SAT won or proved optimal.":
    "Sunucunun son durumunda takip durdu. Başarılı durum, doğrulanmış rapor olduğunu belirtir; CP-SAT'ın kazandığını veya optimaliteyi kanıtladığını göstermez.",
  "Tracking stopped. The last receipt is shown; retry status explicitly when appropriate. No replacement result was invented.":
    "Takip durdu. Son makbuz gösteriliyor; uygun olduğunda durumu açıkça yeniden sorgulayın. Yerine başka sonuç üretilmedi.",
  "Completion won the race; the server kept its successful result.":
    "İş önce tamamlandı; sunucu başarılı sonucunu korudu.",
  "The server confirms cancellation.": "Sunucu iptali doğruladı.",
  "Cancellation accepted; wait for the server to finish native cleanup.":
    "İptal kabul edildi; sunucunun yerel süreç temizliğini bitirmesini bekleyin.",
  "Cancellation outcome is unconfirmed. Refresh the actual status; do not assume the server stopped.":
    "İptal sonucu doğrulanmadı. Gerçek durumu yenileyin; sunucunun durduğunu varsaymayın.",
  "Only local polling paused; the server job was not cancelled.":
    "Yalnızca yerel sorgulama durakladı; sunucudaki iş iptal edilmedi.",
  Monday: "Pazartesi",
  Tuesday: "Salı",
  Wednesday: "Çarşamba",
  Thursday: "Perşembe",
  Friday: "Cuma",
  Saturday: "Cumartesi",
  "Sunday — outside v1 support": "Pazar — v1 desteği dışında",
  "Mature history count": "Olgunlaşmış geçmiş rapor sayısı",
  "Uncensored history count": "Sansürlenmemiş geçmiş rapor sayısı",
  "Recent uncensored attainment mean": "Yakın geçmiş sansürlenmemiş gerçekleşme ortalaması",
  "Recent uncensored attainment standard deviation":
    "Yakın geçmiş sansürlenmemiş gerçekleşme standart sapması",
  "Latest mature report age (hours)": "Son olgunlaşmış raporun yaşı (saat)",
  "Lines & capabilities": "Hatlar ve yetkinlikler",
  "Shifts & breaks": "Vardiyalar ve molalar",
  "Production calendar": "Üretim takvimi",
  "Review & validate": "İncele ve doğrula",
  "Invalid planning assumptions.": "Geçersiz planlama varsayımları.",
  "Enter exact integer offset minutes and complete explicit assumptions.":
    "Kesin tam sayı saat farkını dakika olarak girin ve açık varsayımları tamamlayın.",
  "Unable to read scheduling JSON.": "Çizelgeleme JSON'u okunamadı.",
  "Unable to export this input.": "Bu girdi dışa aktarılamadı.",
  "Planned stops": "Planlı duruşlar",
  "Explicit hypothetical downtime": "Açık varsayımsal duruş",
  "The change does not match the supported input contract.":
    "Değişiklik desteklenen girdi sözleşmesiyle eşleşmiyor.",
  "Review requires a valid exact scenario specification.":
    "İnceleme için geçerli, kesin senaryo tanımı gerekir.",
  "Existing production line": "Mevcut üretim hattı",
  "Existing capacity profile": "Mevcut kapasite profili",
  "Worker count (exact integer)": "İşçi sayısı (kesin tam sayı)",
  "Assumed efficiency (exact fraction 0–1)": "Varsayılan verimlilik (kesin oran 0–1)",
  "Declared line availability": "Tanımlı hat kullanılabilirliği",
  "New assignment ID": "Yeni atama kimliği",
  "Existing shift definition": "Mevcut vardiya tanımı",
  "Existing assignment to remove": "Kaldırılacak mevcut atama",
  "Existing downtime ID": "Mevcut duruş kimliği",
  "New downtime ID": "Yeni duruş kimliği",
  "Declared / explicitly added assignment": "Tanımlı / açıkça eklenen atama",
  "Start timestamp (explicit offset)": "Başlangıç zamanı (açık saat farkıyla)",
  "End timestamp (explicit offset)": "Bitiş zamanı (açık saat farkıyla)",
  "Hypothetical downtime reason": "Varsayımsal duruş nedeni",
  Language: "Dil",
  Turkish: "Türkçe",
  English: "İngilizce",
  "Unrecognized status": "Tanınmayan durum",
  Yes: "Evet",
  No: "Hayır",
  cutting: "Kesim",
  sewing: "Dikim",
  finishing: "Bitim",
  quality_control: "Kalite kontrol",
  packing: "Paketleme",
  day: "Gündüz",
  night: "Gece",
  available: "Kullanılabilir",
  unavailable: "Kullanılamaz",
  "worker-minutes": "işçi-dakika",
  minutes: "dakika",
  pieces: "adet",
  "Worker-min": "İşçi-dk",
  workers: "işçi",
  true: "Evet",
  false: "Hayır",
  disconnected: "Bağlı değil",
  connected: "Bağlı",
  loading: "Yükleniyor",
  error: "Hata",
  ok: "Uygun",
  "Entirely synthetic example; no actual factory observations or performance claims.":
    "Tamamen sentetik örnek; gerçek fabrika gözlemi veya performans iddiası yoktur.",
  "Dedicated qualified crews have constant headcount within each shift; capacity is additive labor only.":
    "Yetkin ve atanmış ekiplerin vardiya içi işçi sayısı sabittir; kapasite yalnızca toplanabilir işçiliktir.",
  "Stage standards and efficiency fractions are hypothetical inputs independent of all ML predictions.":
    "Aşama standartları ve verimlilik oranları tüm ML tahminlerinden bağımsız varsayımsal girdilerdir.",
  "Calendar dates use the supplied shift start offset; overnight shifts belong to their start date.":
    "Takvim tarihleri verilen vardiya başlangıç saat farkını kullanır; gece vardiyaları başlangıç tarihine aittir.",
  "Each order is assessed independently against each full slot; no reservations, splitting, stage scheduling or global feasibility.":
    "Her sipariş tam dilime karşı bağımsız değerlendirilir; rezervasyon, bölme, aşama çizelgelemesi veya bütünsel uygunluk yoktur.",
  "Each order is assessed independently; capacity is never reserved or summed across orders.":
    "Her sipariş bağımsız değerlendirilir; kapasite siparişler arasında ayrılmaz veya toplanmaz.",
  "Stage precedence is declared, but stage timing, WIP, materials and shared resources are not scheduled.":
    "Aşama öncelik ilişkisi tanımlıdır; aşama zamanları, yarı mamul, malzeme ve ortak kaynaklar çizelgelenmez.",
  "Dedicated qualified line crews and stage labor standards are scenario assumptions; no cross-line interchangeability is inferred.":
    "Yetkin atanmış hat ekipleri ve aşama işçilik standartları senaryo varsayımlarıdır; hatlar arası değiştirilebilirlik varsayılmaz.",
  "Efficiency is a declared capacity derating fraction, not an experimental ML prediction.":
    "Verimlilik tanımlı kapasite azaltma oranıdır; deneysel ML tahmini değildir.",
  "Entirely synthetic benchmark; no actual factory performance or ML capacity adjustments.":
    "Tamamen sentetik kıyaslama; gerçek fabrika performansı veya ML kapasite ayarı yoktur.",
  "Dedicated qualified crews, additive stage labor standards and constant line efficiency are hypothetical.":
    "Yetkin atanmış ekipler, toplanabilir aşama işçilik standartları ve sabit hat verimliliği varsayımsaldır.",
  "Whole-stage nonpreemptive operations occupy one uninterrupted working fragment; no splitting, WIP initialization, setups or material constraints.":
    "Tüm aşama, bölünmeden tek kesintisiz çalışma aralığını kullanır; bölme, başlangıç yarı mamulü, hazırlık ve malzeme kısıtları yoktur.",
  "Fixed +03:00 calendar, hard local-midnight releases and soft next-midnight due deadlines.":
    "Sabit +03:00 takvim; başlangıçlar yerel gece yarısında kesin, teslim sınırları ertesi gece yarısında esnektir.",
  "Synthetic research only; not authorized for operational factory decisions.":
    "Yalnızca sentetik araştırma; operasyonel fabrika kararları için yetkilendirilmemiştir.",
  "Demand-censored standard capacity attainment; not intrinsic employee efficiency or guaranteed output.":
    "Talebin sınırladığı standart kapasite gerçekleşme oranı; çalışanın öz verimliliği veya garanti edilen çıktı değildir.",
  "NO_ML_PROMOTION remains unchanged; lower aggregate error does not establish stage superiority.":
    "NO_ML_PROMOTION değişmez; daha düşük genel hata aşama üstünlüğünü göstermez.",
  "Unseen-entity evaluation remains reserved; hidden distribution shift may be undetectable.":
    "Görülmemiş varlık değerlendirmesi ayrılmış kalır; gizli dağılım değişimi saptanamayabilir.",
  "Residual bands are descriptive, uncalibrated and have no coverage guarantee.":
    "Artık aralıkları betimseldir, kalibre edilmemiştir ve kapsama garantisi yoktur.",
  "Hypothetical input differences are not proven causal effects.":
    "Varsayımsal girdi farklarının nedensel etki olduğu kanıtlanmamıştır.",
  "No conversion to assumed_efficiency or mutation of schedules/capacity profiles.":
    "assumed_efficiency değerine dönüşüm, çizelge veya kapasite profili değişikliği yapılmaz.",
  "RF Physics metrics use spent benchmark validation.":
    "RF Physics ölçütleri önceden incelenmiş kıyaslama doğrulamasını kullanır.",
  "RF Physics has no independently calibrated prediction band.":
    "RF Physics için bağımsız olarak kalibre edilmiş tahmin aralığı yoktur.",
  "Hidden disruption risk remains unresolved.": "Gizli aksama riski çözülmedi.",
  "History Boost uses additional mature reports and new development data; this is not an algorithm-only comparison.":
    "History Boost ek olgunlaşmış raporlar ve yeni geliştirme verileri kullanır; bu yalnızca algoritma karşılaştırması değildir.",
  "EXP-010 metrics use equal-world macro averages and online history; inspected results are now spent.":
    "EXP-010 ölçütleri dünyalara eşit ağırlıklı makro ortalamalar ve çevrimiçi geçmiş kullanır; incelenen sonuçlar artık bağımsız değerlendirme için harcanmıştır.",
  "Missing/stale history abstains; the missing-history control was inferior to RF Physics under disruption.":
    "Eksik/eski geçmişte tahmin üretilmez; geçmişsiz kontrol aksama koşulunda RF Physics'ten daha kötüydü.",
  "Baseline actual worst error increased 9.11% versus RF Physics; first unannounced shocks remain unpredictable.":
    "Temel koşuldaki gerçek en yüksek hata RF Physics'e göre %9,11 arttı; habersiz ilk şoklar öngörülemez.",
  "No calibrated candidate band, factory validation or operational promotion is established.":
    "Kalibre edilmiş aday aralığı, fabrika doğrulaması veya operasyonel kullanım onayı yoktur.",
  "Conditional hypothetical capacity change; no causal or factory-productivity claim.":
    "Koşullu varsayımsal kapasite değişikliği; nedensellik veya fabrika verimliliği iddiası yoktur.",
  "Entirely synthetic; additive qualified labor and declared efficiency are uncalibrated assumptions.":
    "Tamamen sentetik; toplanabilir yetkin işçilik ve tanımlı verimlilik kalibre edilmemiş varsayımlardır.",
  "One full batch per uninterrupted fragment; no material, setup, sharing or ML assumptions.":
    "Kesintisiz aralık başına tek tam parti; malzeme, hazırlık, paylaşım veya ML varsayımı yoktur.",
  "Conditional scenario additional-workers; source synthetic:m04-worked-examples.":
    "Koşullu additional-workers senaryosu; kaynak synthetic:m04-worked-examples.",
  "Conditional synthetic planning; no causal, forecast or financial guarantee.":
    "Koşullu sentetik planlama; nedensellik, tahmin veya finansal garanti yoktur.",
  "Declared qualified labor, standards and efficiency are uncalibrated assumptions.":
    "Tanımlı yetkin işçilik, standartlar ve verimlilik kalibre edilmemiş varsayımlardır.",
  "No sharing, setups, materials, splitting, rework, WIP or ML-derived capacity.":
    "Paylaşım, hazırlık, malzeme, bölme, yeniden işleme, yarı mamul veya ML kaynaklı kapasite yoktur.",
  "Wall-limited optimizer outcomes may differ; candidate proof remains explicit.":
    "Süre sınırına bağlı optimizasyon sonuçları değişebilir; aday kanıtı açıkça gösterilir.",
  "Completed-order tardiness excludes unfinished demand; denominators can change.":
    "Tamamlanan sipariş gecikmesi kalan talebi dışlar; paydalar değişebilir.",
  "Entirely synthetic analytical benchmark with one dedicated worker and one standard worker-minute per piece.":
    "Tek atanmış işçi ve adet başına bir standart işçi-dakikayla tamamen sentetik analitik kıyaslama.",
  "Ten-minute horizon, whole batches6/5/5; priorities1/2/3; previous-day soft due dates.":
    "On dakikalık ufuk, 6/5/5 adet tam parti; 1/2/3 öncelik; önceki gün esnek teslim tarihleri.",
  "No interruptions, setup, sharing, initial WIP, splitting or ML capacity adjustment.":
    "Kesinti, hazırlık, paylaşım, başlangıç yarı mamulü, bölme veya ML kapasite ayarı yoktur.",
  Cutting: "Kesim",
  Sewing: "Dikim",
  Finishing: "Son işlemler",
  "Quality control": "Kalite kontrol",
  Packing: "Paketleme",
  Synthetic: "Sentetik",
  Disconnected: "Bağlı değil",
  Connected: "Bağlı",
  Loading: "Yükleniyor",
  Error: "Hata",
  Healthy: "Sağlıklı",
  "Capacity assessed": "Kapasite değerlendirildi",
  "Valid complete schedule": "Geçerli tam çizelge",
  "Valid partial schedule": "Geçerli kısmi çizelge",
  "Valid comparison": "Geçerli karşılaştırma",
  "Valid input": "Geçerli girdi",
  Invalid: "Geçersiz",
  Completed: "Tamamlandı",
  Unscheduled: "Çizelgelenmedi",
  Partial: "Kısmi",
  Queued: "Kuyrukta",
  Running: "Çalışıyor",
  Succeeded: "Başarılı",
  Failed: "Başarısız",
  Cancelled: "İptal edildi",
  Expired: "Süresi doldu",
  Terminal: "Son durum",
  "Starting worker": "Alt süreç başlatılıyor",
  "Worker running": "Alt süreç çalışıyor",
  "Cleaning up": "Kaynaklar temizleniyor",
  Scheduling: "Çizelgeleme",
  Scenarios: "Senaryolar",
  Greedy: "Açgözlü yöntem",
  "CP-SAT": "CP-SAT",
  "Greedy with CP-SAT": "CP-SAT ile açgözlü yöntem",
  Better: "Daha iyi",
  Worse: "Daha kötü",
  Tie: "Eşit",
  "Not comparable": "Karşılaştırılamaz",
  Defined: "Tanımlı",
  "Zero baseline": "Referans sıfır",
  "Both zero": "İkisi de sıfır",
  "Not assessed": "Değerlendirilmedi",
  Optimal: "Optimal",
  "Feasible, optimality unproven": "Uygulanabilir, optimalite kanıtlanmadı",
  Infeasible: "Uygulanamaz",
  Unknown: "Bilinmiyor",
  "Invalid solver model": "Geçersiz çözücü modeli",
  "Not requested": "İstenmedi",
  "CP-SAT not requested": "CP-SAT istenmedi",
  "No strict improvement": "Kesin iyileşme yok",
  "Greedy retained": "Açgözlü çözüm korundu",
  "Candidate not better": "Aday daha iyi değil",
  "No accepted candidate": "Kabul edilmiş aday yok",
  "Resource limit": "Kaynak sınırı",
  "Time limit": "Süre sınırı",
  "Stage mismatch": "Aşama uyumsuzluğu",
  "Style not supported": "Ürün modeli desteklenmiyor",
  "Line unavailable": "Hat kullanılamaz",
  "No workers": "İşçi yok",
  "No working time": "Çalışma süresi yok",
  "Zero efficiency": "Sıfır verimlilik",
  "Before release date": "Başlangıç tarihinden önce",
  "After due date": "Teslim tarihinden sonra",
  "Insufficient capacity": "Yetersiz kapasite",
  "No sufficient independent slot": "Yeterli bağımsız dilim yok",
  "No compatible slot": "Uyumlu dilim yok",
  "No eligible line": "Uygun hat yok",
  "No available capacity": "Kullanılabilir kapasite yok",
  "Release after horizon": "Başlangıç planlama ufkunun dışında",
  "Requires splitting or preemption": "Bölme veya kesinti gerekiyor",
  "Horizon exhausted": "Planlama ufku tükendi",
  "Capacity reserved": "Kapasite ayrılmış",
  "Predecessor unscheduled": "Önceki aşama çizelgelenmedi",
  "Supported experimental input": "Desteklenen deneysel girdi",
  "Review required": "İnceleme gerekli",
  "Experimental, not promoted": "Deneysel, kullanıma alınmadı",
  "Baseline comparison only": "Yalnızca referans karşılaştırması",
  "Research candidate": "Araştırma adayı",
  "Experimental history candidate": "Deneysel geçmiş bağlamı adayı",
  "Within declared feature support only": "Yalnızca tanımlı özellik desteği içinde",
  "Mature history required": "Olgunlaşmış geçmiş gerekli",
  "Hypothetical history not source verified": "Varsayımsal geçmişin kaynağı doğrulanmadı",
  "No operational ML promotion": "ML operasyonel kullanıma alınmadı",
  "Trusted experimental model artifacts unavailable":
    "Güvenilir deneysel model dosyaları kullanılamıyor",
  "Server busy": "Sunucu meşgul",
  "Job queue full": "İş kuyruğu dolu",
  "Job registry full": "İş kayıt alanı dolu",
  "Retained results fill the memory budget": "Saklanan sonuçlar bellek bütçesini dolduruyor",
  "Unsupported job solver configuration": "Desteklenmeyen iş çözücü ayarları",
  "Job not found": "İş bulunamadı",
  "Job expired": "İşin süresi doldu",
  "Job not ready": "İş hazır değil",
  "Job failed": "İş başarısız",
  "Job cancelled": "İş iptal edildi",
  "Complexity limit exceeded": "Karmaşıklık sınırı aşıldı",
  "Conflicting scenario edits": "Çakışan senaryo değişiklikleri",
  "Invalid input": "Geçersiz girdi",
  "Request body too large": "İstek gövdesi çok büyük",
  "Execution deadline reached": "Çalıştırma süre sınırına ulaştı",
  "Job service unavailable": "İş hizmeti kullanılamıyor",
  "Job expired in queue": "İşin kuyrukta süresi doldu",
  "Response limit exceeded": "Yanıt sınırı aşıldı",
  "Execution failed": "Çalıştırma başarısız",
  "Process isolation unavailable": "Süreç yalıtımı kullanılamıyor",
  "Experimental inference": "Deneysel tahmin",
  "Experimental synthetic only": "Yalnızca deneysel sentetik kullanım",
  "Set workers": "İşçi sayısını ayarla",
  "Set efficiency": "Verimliliği ayarla",
  "Set availability": "Kullanılabilirliği ayarla",
  "Add assignment": "Atama ekle",
  "Remove assignment": "Atama kaldır",
  "Add downtime": "Duruş ekle",
  "Replace downtime": "Duruşu değiştir",
  "Remove downtime": "Duruş kaldır",
  orders: "sipariş",
  operations: "operasyon",
  "stage-pieces": "aşama-adet",
  "priority-weighted minutes": "öncelik ağırlıklı dakika",
  "line-minutes": "hat-dakika",
  "worker-minutes per piece": "adet başına işçi-dakika",
  ratio: "oran",
  Disruption: "Aksama koşulu",
  "Production data workspace": "Üretim verileri çalışma alanı",
  NO_ML_PROMOTION: "NO_ML_PROMOTION",
  "Saved capacity report · explicit demo mode": "Kayıtlı kapasite raporu · açık demo modu",
  "Synthetic data editor": "Sentetik veri düzenleyicisi",
  "Interactive planning": "Etkileşimli planlama",
  "Read-only inspection": "Salt okunur inceleme",
  "Available time × declared workers": "Kullanılabilir süre × tanımlı işçi sayısı",
  "Independent estimates · elapsed minutes per assignment":
    "Bağımsız tahminler · atama başına geçen dakika",
  "Capacity assessment does not allocate work": "Kapasite değerlendirmesi atama yapmaz",
  "This dataset has a saved proposal. Load it explicitly to inspect its verified partial outcome.":
    "Bu veri kümesinde kayıtlı öneri var. Doğrulanmış kısmi sonucu incelemek için açıkça yükleyin.",
  "Saved verification fixture": "Kayıtlı doğrulama örneği",
  "Existing proposal reverified by the local API": "Yerel API tarafından yeniden doğrulanan öneri",
  "Only the eight existing change operations are supported":
    "Yalnızca mevcut sekiz işlem desteklenir",
  "All fields are included in the strict versioned scenario request":
    "Tüm alanlar katı, sürümlü senaryo isteğine dâhildir",
  "Exact scenario specification": "Kesin senaryo tanımı",
  "The consolidated CSV and capacity exports are inspection data, not executable scheduling instances.":
    "Birleştirilmiş CSV ve kapasite dışa aktarımları inceleme verisidir; çalıştırılabilir çizelgeleme örneği değildir.",
  "Inputs exceeding this HTTP envelope are unsupported and never truncated. Jobs use server-fixed seed 42, worker 1, 1 s wall / 1 deterministic unit per phase.":
    "Bu HTTP sınırını aşan girdiler desteklenmez ve kesilmez. İşler sunucuda sabit tohum 42, iş parçacığı 1 ve faz başına 1 sn gerçek süre / 1 deterministik birim kullanır.",
  "Local-only workspace": "Yalnızca yerel çalışma alanı",
  "Independent assessment reports": "Bağımsız değerlendirme raporları",
  "Real-data research remains offline; synthetic predictions are separate":
    "Gerçek veri araştırması çevrimdışıdır; sentetik tahminler ayrı sunulur",
  "Server metadata; dedicated job views submit, track and cancel bounded work":
    "Sunucu üst verileri; ilgili iş sayfalarından sınırlı işler gönderilir, izlenir ve iptal edilir",
  "Explore independent order-stage-slot assessments.":
    "Bağımsız sipariş–aşama–dilim değerlendirmelerini inceleyin.",
  "Backend capabilities describe the API. Planning, scenarios, jobs and experimental predictions are available in their dedicated views.":
    "Sunucu yetenekleri API'nin olanaklarını tanımlar. Planlama, senaryo, iş ve deneysel tahmin işlemleri ilgili sayfalarda sunulur.",
  "Complete this required field.": "Bu zorunlu alanı doldurun.",
  "Enter a valid value in the requested format.": "İstenen biçimde geçerli bir değer girin.",
  "Enter a value within the displayed limits.": "Gösterilen sınırlar içinde bir değer girin.",
  "Check the required text length.": "Gerekli metin uzunluğunu kontrol edin.",
  "Use the requested format and allowed characters.":
    "İstenen biçimi ve izin verilen karakterleri kullanın.",
  "Enter a valid number with the required precision.":
    "Gerekli hassasiyette geçerli bir sayı girin.",
  "Macro R²": "Makro R²",
  "Baseline condition": "Temel koşul",
  "Loopback API with one shared secret; HTTPS gateway requires explicit setup.":
    "Tek ortak anahtarlı geri döngü API'si; HTTPS ağ geçidi açık kurulum gerektirir.",
  "Synthetic conditional results require human review.":
    "Sentetik koşullu sonuçlar insan incelemesi gerektirir.",
  "No database, durable jobs or automatic production decisions.":
    "Veritabanı, kalıcı işler veya otomatik üretim kararları yoktur.",
  "M01 remains offline; M08C synthetic models are experimental only.":
    "Gerçek veri çalışması çevrimdışıdır; sentetik modeller yalnızca deneyseldir.",
  "Synthetic conditional planning; not production authorization.":
    "Sentetik koşullu planlama; üretim yetkilendirmesi değildir.",
  "Only whole-stage-minute-v1 is verified; proof belongs to its producer.":
    "Yalnızca whole-stage-minute-v1 doğrulanır; kanıt çözümü üreten yönteme aittir.",
  "No ML capacity, shared crews, materials, setups, splitting or initial WIP.":
    "ML kapasitesi, ortak ekip, malzeme, hazırlık, bölme veya başlangıç yarı mamulü yoktur.",
  "Synthetic planned stop overlapping lunch.": "Öğle molasıyla çakışan sentetik planlı duruş.",
  "Synthetic second stop overlapping the first.": "İlk duruşla çakışan sentetik ikinci duruş.",
  "Synthetic unavailability partly overlapping the planned stop.":
    "Planlı duruşla kısmen çakışan sentetik kullanılamazlık.",
  "Explicit hypothetical maintenance": "Açık varsayımsal bakım",
  "Hypothetical additional stop": "Varsayımsal ek duruş",
  "Hypothetical revised maintenance": "Varsayımsal güncellenmiş bakım",
  "Dedicated qualified cutting crew for this synthetic style.":
    "Bu sentetik ürün modeli için atanmış yetkin kesim ekibi.",
  "Dedicated qualified sewing crew for this synthetic style.":
    "Bu sentetik ürün modeli için atanmış yetkin dikim ekibi.",
  "Dedicated qualified finishing crew for this synthetic style.":
    "Bu sentetik ürün modeli için atanmış yetkin son işlem ekibi.",
  "Outside training support: {p0}": "Eğitim desteği dışında: {p0}",
  "Additional backend limitation": "Ek sunucu sınırlaması",
  "Capacity assessment": "Kapasite değerlendirmesi",
  "Reference scheduling": "Referans çizelgeleme",
  "Schedule verification": "Çizelge doğrulama",
  "Scenario comparison": "Senaryo karşılaştırması",
  "Input validation": "Girdi doğrulama",
  "Exact feature schema required": "Kesin özellik şeması gerekli",
  "Unsupported categorical input": "Desteklenmeyen kategorik girdi",
  "Invalid numeric input": "Geçersiz sayısal girdi",
  "Zero planned capacity, undefined target": "Planlı kapasite sıfır, hedef tanımsız",
  "Invalid or unsupported physical input": "Geçersiz veya desteklenmeyen fiziksel girdi",
  "Invalid or physically unsupported prediction":
    "Geçersiz veya fiziksel olarak desteklenmeyen tahmin",
  "Prediction outside training target support": "Tahmin eğitim hedefi desteğinin dışında",
  "Minimum stage sample count": "En az aşama örnek sayısı",
  "All-stage noninferiority": "Tüm aşamalarda daha kötü olmama",
  "Stage noninferiority": "Aşamada daha kötü olmama",
  "Tail noninferiority": "Kuyruk hatasında daha kötü olmama",
  "MAE improvement": "MAE iyileşmesi",
  "Stage MAE noninferiority": "Aşama MAE değerinde daha kötü olmama",
  "P90 noninferiority": "P90 değerinde daha kötü olmama",
  "P95 noninferiority": "P95 değerinde daha kötü olmama",
  "Worst-error noninferiority": "En yüksek hatada daha kötü olmama",
  "Minimum stage support": "En az aşama desteği",
  "CP-SAT not strictly better": "CP-SAT kesin olarak daha iyi değil",
  "Not run": "Çalıştırılmadı",
  "No feasible incumbent": "Uygulanabilir mevcut çözüm yok",
  "Unknown, earlier verified solution retained": "Bilinmiyor, önceki doğrulanmış çözüm korundu",
  "Skipped at resource limit": "Kaynak sınırında atlandı",
  "Terminated at resource limit": "Kaynak sınırında sonlandırıldı",
  "Memory limit exceeded": "Bellek sınırı aşıldı",
  "Adapter rejected candidate": "Uyarlayıcı adayı reddetti",
  "Independent verifier rejected candidate": "Bağımsız doğrulayıcı adayı reddetti",
  "Feasible phase, optimality unproven": "Uygulanabilir faz, optimalite kanıtlanmadı",
  "All three objectives proven optimal": "Üç amacın tümünde optimalite kanıtlandı",
  "Undefined for zero baseline": "Sıfır referans için tanımsız",
  "Undefined for missing metric": "Eksik ölçüt için tanımsız",
  "Synthetic dedicated crew assumed qualified for this exact style/stage; no transfers, shared workers or role bottlenecks modeled.":
    "Bu ürün modeli/aşama için yetkin varsayılan sentetik atanmış ekip; transfer, ortak işçi veya görev darboğazı modellenmez.",
  "Hypothetical dedicated qualified crew": "Varsayımsal atanmış yetkin ekip",
  "Explicit hypothetical qualification": "Açık varsayımsal yetkinlik",
  "Improvement in every baseline world": "Her temel koşul dünyasında iyileşme",
  "Macro improvement": "Makro iyileşme",
  "Overprediction guard": "Aşırı tahmin eşiği",
  "Stage regression guard": "Aşama gerileme eşiği",
  "Stress macro guard": "Stres makro eşiği",
  "Stress world guard": "Stres dünyası eşiği",
  "Improvement over strongest outer naive baseline": "En güçlü dış naif referansa göre iyileşme",
  "Temporal wins": "Zamansal üstünlükler",
  "Worst-error guard": "En yüksek hata eşiği",
  "Line capability": "Hat yetkinliği",
  "Shift assignment": "Vardiya ataması",
  "Unavailable period": "Kullanılamayan dönem",
  Changed: "Değişti",
  "This input is a capacity scenario, not an executable scheduling instance. Select a scheduling or scenario instance.":
    "Bu girdi bir kapasite senaryosudur, çalıştırılabilir çizelgeleme örneği değildir. Bir çizelgeleme veya senaryo örneği seçin.",
  "Local synthetic garment planning inspection. No live factory data.":
    "Yerel sentetik hazır giyim üretim planlama incelemesi. Canlı fabrika verisi yoktur.",
  "Varied crews, downtime and independent checks":
    "Farklı ekipler, duruşlar ve bağımsız kontroller",
  "One shared line and a saved partial schedule": "Tek ortak hat ve kayıtlı kısmi çizelge",
  "One qualified crew, downtime and a declared reserve shift":
    "Yetkin bir ekip, duruş ve tanımlı yedek vardiya",
  "Additional capacity can worsen greedy choices":
    "Ek kapasite, açgözlü yöntemin seçimlerini kötüleştirebilir",
  "Multiple stages, routing and late completions":
    "Birden fazla aşama, rotalar ve geciken tamamlanmalar",
  "User-defined synthetic assumptions, validated by local Python":
    "Kullanıcının tanımladığı, yerel Python ile doğrulanmış sentetik varsayımlar",
  "Missing metric value": "Eksik ölçüt değeri",
} as const;
