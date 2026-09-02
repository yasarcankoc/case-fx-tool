# Notlar

## Kararlar

**`rate_date` upstream'den okunur.** İşin özü burası. Upstream cevabındaki `date`
alanı kurun gerçekten hangi güne ait olduğunu söylüyor; sorulan tarihi geri
yazmak kolay ama yanlış olurdu. Cumartesi sorulan bir kur cuma kuruysa cevap
bunu gösterir. Model müşteriye yanlış tarih söylemesin diye `asked_date` de ayrı
bir alan olarak duruyor.

**Cache anahtarında tarih var.** `(from, to, date)` üçlüsü. Tarihsiz sorgular
hiç cache'lenmiyor: bugünün kuru gün içinde güncellenebiliyor ve eski kur
döndürmektense her seferinde sormayı tercih ettim. Geçmiş tarihler değişmediği
için onlarda süre sınırı koymadım.

**Kur yuvarlanmıyor, sadece sonuç yuvarlanıyor.** Kuru iki ondalığa yuvarlayıp
çarpmak büyük tutarlarda ciddi fark yaratıyor: 1.000.000 EUR'da yaklaşık 4.500 TL.
Çarpma ham kurla yapılıyor, `result` iki ondalığa yuvarlanıyor.

**Tutarda iki ondalık sınırı.** Para tutarları iki ondalıkla ifade edilir; daha
fazlası sessizce yuvarlanmak yerine reddediliyor, çünkü çağıran taraf ne
gönderdiğini bilmeli.

**Aynı para birimi upstream'e sorulmuyor.** 1.0 kuru tanım gereği doğru ve ECB
yayınına bağlı değil. Gereksiz istek atmamak için kısa devre yapılıyor, bu
yüzden `rate_date` sorulan tarihe eşit.

**Hatalar tek yerden yönetiliyor.** `FxError` sınıfı kod, mesaj ve HTTP status
taşıyor; tek bir exception handler bunları `{error, message}` biçimine çeviriyor.
Yeni bir hata durumu eklemek tek satır.

## Bilinen sınırlar

- Cache süreç içinde tutuluyor, birden fazla instance'ta paylaşılmıyor.
  Gerçek dağıtımda Redis'e taşınmalı.
- Yapılandırılmış log eklerdim: hangi isteğin hangi upstream çağrısına
  dönüştüğü şu an görünmüyor.
- `amount` float olarak işleniyor. Tek bir çarpma yapıldığı ve sonuç iki
  ondalığa yuvarlandığı için pratikte kayıp yok; ama zincirleme hesap veya
  toplama girseydi `Decimal` gerekirdi.