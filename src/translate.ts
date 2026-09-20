// Cloudflare Workers AI çeviri modeli. Çeviri başarısız olursa
// orijinal (İngilizce) metni döner — sayfa asla boş kalmaz.
export async function turkceyeCevir(ai: Ai, metin: string): Promise<string> {
  const girdi = metin.trim();
  if (!girdi) return girdi;

  try {
    const sonuc = (await ai.run("@cf/meta/m2m100-1.2b", {
      text: girdi,
      source_lang: "english",
      target_lang: "turkish",
    })) as { translated_text?: string };

    return sonuc.translated_text?.trim() || girdi;
  } catch (hata) {
    console.error("Çeviri hatası:", hata);
    return girdi;
  }
}

// Rakam dizisi seçildi: çeviri modelleri noktalama/sembolleri bozabiliyor
// ama sayıları neredeyse her zaman olduğu gibi bırakıyor.
const AYRAC = "739502617385";
const AYRAC_RE = /\d{6,}/;

// Başlık ve özeti TEK bir AI çağrısında çevirir. Cloudflare Workers'ın
// istek başına alt-istek sınırı (ücretsiz planda 50) her haber için ayrı
// ayrı çeviri çağrısı yapıldığında hızla aşılıyordu; bu yüzden ikisi
// birleştirilip tek çağrıda çevriliyor.
export async function baslikVeOzetCevir(
  ai: Ai,
  baslik: string,
  ozet: string
): Promise<{ baslik: string; ozet: string }> {
  const birlesik = `${baslik}\n${AYRAC}\n${ozet}`;
  const cevrilmis = await turkceyeCevir(ai, birlesik);

  const parcalar = cevrilmis.split(AYRAC_RE);
  if (parcalar.length >= 2) {
    return { baslik: parcalar[0].trim(), ozet: parcalar.slice(1).join(" ").trim() };
  }

  // Model ayıracı bozduysa: başlığı orijinal bırak, tüm çeviriyi özet yap.
  return { baslik, ozet: cevrilmis.trim() };
}
