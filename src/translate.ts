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
