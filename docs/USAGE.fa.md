# راهنمای استفاده

[English](USAGE.md) · [بازگشت به راهنمای فارسی](../README.fa.md)

فرمان‌ها را در پوشهٔ اصلی مخزن اجرا کنید. در صورت نصب بسته، فرمان scf-toolkit نیز همان آرگومان‌ها را می‌پذیرد.

[قواعد نگاشت و STRM با مثال](STRM.fa.md)

## ۱. بررسی نمونهٔ همراه بسته

~~~bash
python skills/scf-mapping-translation/scripts/run.py validate --catalog examples/synthetic/catalog.json --inventory examples/synthetic/inventory.json --ledger examples/synthetic/ledger.json
python skills/scf-mapping-translation/scripts/run.py build-xlsx --catalog examples/synthetic/catalog.json --inventory examples/synthetic/inventory.json --ledger examples/synthetic/ledger.json --out local-data/demo.xlsx
python skills/scf-mapping-translation/scripts/run.py check-xlsx --catalog examples/synthetic/catalog.json --inventory examples/synthetic/inventory.json --ledger examples/synthetic/ledger.json --xlsx local-data/demo.xlsx
~~~

وضعیت‌های ساختاری مورد انتظار READY_FOR_EXPORT و SAVED_XLSX_VERIFIED هستند؛ این وضعیت‌ها صحت معنایی نگاشت را تأیید نمی‌کنند. نمونه عمداً شامل دو تعهد مستقل است: یکی دارای نگاشت و دیگری بدون رابطه. بازبینی‌های نمونه ساختگی‌اند.

## ۲. آماده‌سازی فهرست منابع واقعی

ساختار اسناد و الزامات را مطابق examples/synthetic/inventory.json بسازید. برای هر سند، source_id مستقل، نسخه و SHA-256 اصل فایل ثبت کنید. متن دقیق، شمارهٔ بند مادر، صفحات فیزیکی PDF و مقدمهٔ مشترک را نگه دارید. پیش از تأیید بازبینی منبع، ابهام استخراج را با تصویر اصل سند رفع کنید.

تعهدها را با معیار قبولی یا رد مستقل تفکیک کنید. قطعه‌های دقیق متن را به ترتیب منبع و با حفظ قیود موروثی نگه دارید. فقط اگر نقل پیوسته ممکن نیست از متن ترکیبی با دلیل صریح استفاده کنید. قید غایب را با قید ساخته‌شده اشتباه نگیرید. هش فهرست منابع و کاتالوگ SCF را در فرادادهٔ دفتر تصمیم‌ها (ledger) ثبت کنید؛ تغییر هش فقط پس از بازبینی آگاهانهٔ ورودی تغییرکرده انجام شود.

## ۳. یافتن و داوری نامزدها

~~~bash
python skills/scf-mapping-translation/scripts/run.py shortlist --catalog local-data/scf-2026.2.json --query "کنترل دسترسی فیزیکی" --k 15 --out local-data/candidates.json
~~~

جست‌وجوی BM25 متن AO را نیز بررسی می‌کند. پل فارسی ابزار محدودی برای بازیابی است، نه مترجم عمومی یا تحلیلگر صرفی. نتیجهٔ ضعیف یا خالی به جست‌وجوی گسترده‌تر و بررسی دستی حوزه و AO نیاز دارد. retrieval_score را به قدرت رابطه تبدیل نکنید و نامزد اول را بدون مقایسه نپذیرید.

برای هر تعهد، دامنهٔ واقعی جست‌وجو و تصمیم نامزدها، نقل دقیق کنترل/AO، گزینه‌های جایگزین، شواهد شمول و تفاوت دامنه‌ها، دلیل امتیاز و بازبینی‌ها ثبت شوند. پروفایل ثابت از تغییر بی‌صدای Equal / Equal To یا مبنای استدلال جلوگیری می‌کند. **فقط امتیاز صحیح ۵ تا ۱۰، شامل خود ۵، قابل پذیرش است؛ ۱ تا ۴ حتی به‌عنوان fallback رد می‌شود.** اگر هیچ نامزدی واجد شرایط نبود، No Relationship با دلیل بازبینی‌شده و خانه‌های خالی کنترل و امتیاز ثبت کنید.

برای هر تعهد نگاشت‌شده، دلیل پوشش ترکیبی و فهرست صریح بندهای باقیمانده، حتی اگر خالی باشد، لازم است. این موارد نتیجهٔ بازبینی ثبت‌شده‌اند، نه اثبات خودکار اجتماع مجموعه‌ها. تصمیم حل‌نشده مانع خروجی است. [قرارداد کامل داده](../skills/scf-mapping-translation/references/data-contract.md).

## ۴. اعتبارسنجی و خروجی

~~~bash
python skills/scf-mapping-translation/scripts/run.py validate --catalog local-data/scf-2026.2.json --inventory local-data/inventory.json --ledger local-data/ledger.json --report local-data/validation.json
python skills/scf-mapping-translation/scripts/run.py build-xlsx --catalog local-data/scf-2026.2.json --inventory local-data/inventory.json --ledger local-data/ledger.json --out local-data/mapping.xlsx
python skills/scf-mapping-translation/scripts/run.py check-xlsx --catalog local-data/scf-2026.2.json --inventory local-data/inventory.json --ledger local-data/ledger.json --xlsx local-data/mapping.xlsx
~~~

اعتبارسنجی در نخستین خطای مسدودکننده توقف می‌کند و علت را گزارش می‌دهد؛ پس از اصلاح دوباره اجرا کنید. خروجی دقیقاً یک برگهٔ قابل مشاهدهٔ STRM Mapping با ده ستون ثابت دارد. نام و شرح کنترل از کاتالوگ ثابت می‌آیند. شناسهٔ منبع، تعهد فرزند، صفحه و توضیح شکاف در Notes قرار می‌گیرند. شناسه‌ها متن صریح و امتیازها عدد هستند. مقدمهٔ بند مادر فقط در اولین ردیف نمایشی می‌آید، ولی قیود موروثی برای همهٔ فرزندان در دادهٔ داخلی حفظ می‌شوند.

الگوی اختیاری --template باید ده عنوان دقیق در ردیف نخست و ده ستون ادغام‌نشده داشته باشد. الگو فقط ورودی است و مسیر خروجی باید متفاوت باشد. برگه‌های اضافی الگو صادر نمی‌شوند. صادرکننده ابعاد پنهان و سبک متن را بازنشانی می‌کند؛ بررسی فایل ذخیره‌شده ردیف/ستون پنهان، فرمول، پیوند، مقدار تغییریافته و رنگ متن ناخوانا را رد می‌کند. تطبیق مقدار، ممیزی کامل ظاهر یا چاپ نیست؛ برای متن‌های بلند ممکن است افزایش ارتفاع ردیف در Excel لازم باشد.

ابتدا فایل موقت ساخته و تطبیق داده می‌شود و سپس به‌صورت اتمی به مسیر خروجی منتقل می‌شود. شکست خروجی نباید فایل نهایی موجود را جایگزین کند. شرح SCF در خروجی پیش‌فرض انگلیسی اصلی است؛ ترجمهٔ بازبینی‌شده دادهٔ دوزبانهٔ جداگانه باقی می‌ماند، مگر مسیر نمایش جداگانه‌ای صریحاً پیاده‌سازی و بررسی شود.

## ۵. ترجمه و بازبینی

از دستورالعمل ترجمهٔ مهارت برای تولید فارسی وفادار استفاده کنید. ابزار خط فرمان، واژگان و کنترل کیفیت فراهم می‌کند؛ مترجم خودکار مبتنی بر مدل نیست.

~~~bash
python skills/scf-mapping-translation/scripts/run.py lookup --references local-data/references --text "Access Control Policy and authentication are required."
python skills/scf-mapping-translation/scripts/run.py translation-qa examples/synthetic/translations.jsonl
python skills/scf-mapping-translation/scripts/run.py translation-qa local-data/translations.jsonl --references local-data/references --report local-data/translation-qa.json
~~~

هر واحد ترجمه به بازبینی معنایی با ثبت صادقانه نیاز دارد. تصمیم واژگانی باید به مدخل مجاز، عبارت منطبق منبع، دلیل بافتی و معادل فارسی عیناً نقل‌شده ارجاع دهد. انتخاب مرجع تکمیلی با وجود نامزد افتا، به دلیل مستند عدم تطابق معنا نیاز دارد. مدخل تعلیق‌شده قابل استناد نیست. اصطلاح ناشناخته یا پیشنهادی را جداگانه و غیرمصوب ثبت کنید؛ شناسهٔ مدخل نسازید.

بررسی شناسه، عدد و نفی ابتکاری است و ممکن است هشدار اضافی بدهد یا خطایی را نبیند. نتیجهٔ پاک هم به بازبینی کامل معنا و اصطلاحات نیاز دارد. READY_FOR_SEMANTIC_REVIEW وضعیت کنترل کیفیت است، نه مجوز ادعای تأیید تخصصی.

## کدهای خروج

- ۰: عملیات قابل بررسی ماشینی موفق بوده است.
- ۱: اعتبارسنجی داده، خروجی یا کنترل کیفیت به اصلاح یا بازبینی نیاز دارد.
- ۲: خطا در نحوهٔ استفاده از فرمان.

بازبینی مدل و بازبینی انسان باید صریحاً متمایز بمانند.
