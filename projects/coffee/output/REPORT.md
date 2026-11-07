# Taipei coffee shops × food bloggers (Instagram)

Interactive graph: `index.html` (open in a browser; click a node to see who tagged it).
Full data: `food_creators.csv`, `food_bloggers.csv`, `graph.json`.

**Edge A → B** = A tagged / @mentioned / co-posted with B in one of A's 12 most recent posts.
Links between affiliated accounts (sister shops, an owner tagging their own shop) are excluded.
**Bloggers / Makers** = how many distinct food bloggers / food makers tagged the account.
**Taste (creators)** = PageRank over the endorsement graph (1.0 = average).
**Taste (bloggers)** = Σ over makers they tag of log₂(1 + other accounts that also tagged that maker).

## Top 50 coffee shops by followers (194 total)

| # | Account | Name | Type | Followers | Tagged by bloggers | Tagged by makers | Taste |
|---|---|---|---|---|---|---|---|
| 1 | [@barista_ray](https://www.instagram.com/barista_ray/) | 張睿 BARISTA RAY ˙Ⱉ˙ฅ🩵 | café (barista) | 38.0K | 1 | 1 | 0.99 |
| 2 | [@kasasagicoffee](https://www.instagram.com/kasasagicoffee/) | 鵲KASASAGI COFFEE ROASTERS | roastery | 37.1K | 0 | 1 | 1.18 |
| 3 | [@fakesobertaipei](https://www.instagram.com/fakesobertaipei/) | Fake Sober Coffee & Bar | café | 27.6K | 0 | 0 | 0.78 |
| 4 | [@simplekaffa](https://www.instagram.com/simplekaffa/) | SIMPLE KΛFFΛ, Taipei | café | 23.8K | 0 | 0 | 0.78 |
| 5 | [@coffeestopover](https://www.instagram.com/coffeestopover/) | coffee stopover | café | 22.7K | 0 | 4 | 2.52 |
| 6 | [@soonsoon_house](https://www.instagram.com/soonsoon_house/) | 順順 | café | 21.4K | 0 | 0 | 0.78 |
| 7 | [@vwibychadwang](https://www.instagram.com/vwibychadwang/) | VWI by CHADWANG | café | 21.2K | 0 | 1 | 1.08 |
| 8 | [@sidoli_radio](https://www.instagram.com/sidoli_radio/) | SIDOLI RADIO 小島裡 | café | 20.5K | 0 | 0 | 0.78 |
| 9 | [@phase_coffee_roasters](https://www.instagram.com/phase_coffee_roasters/) | Phase Coffee Roasters | roastery | 20.2K | 1 | 10 | 5.92 |
| 10 | [@ironwood.coffee](https://www.instagram.com/ironwood.coffee/) | 鐵木 Ironwood Coffee | café | 19.8K | 0 | 0 | 0.78 |
| 11 | [@mountaintowncoffeeroasters](https://www.instagram.com/mountaintowncoffeeroasters/) | Mountaintown Coffee Roasters | roastery | 18.1K | 1 | 1 | 0.98 |
| 12 | [@stablenice.bldg](https://www.instagram.com/stablenice.bldg/) | StableNice BLDG. | café | 17.1K | 0 | 1 | 0.93 |
| 13 | [@tzubi_coffee](https://www.instagram.com/tzubi_coffee/) | Tzubi Coffee / 趣未商行 | roastery | 16.8K | 0 | 0 | 0.78 |
| 14 | [@noon.taipei](https://www.instagram.com/noon.taipei/) | n o o n | café | 16.7K | 1 | 1 | 1.43 |
| 15 | [@oasis_coffee_roasters_anhe](https://www.instagram.com/oasis_coffee_roasters_anhe/) | Oasis Coffee Roasters | roastery | 16.4K | 0 | 0 | 0.78 |
| 16 | [@dunekoffee](https://www.instagram.com/dunekoffee/) | 沙丘 | café | 16.3K | 0 | 0 | 0.78 |
| 17 | [@coffee_dumbo](https://www.instagram.com/coffee_dumbo/) | 登波咖啡COFFEE DUMBO | café | 15.8K | 0 | 0 | 0.78 |
| 18 | [@taiwan_rememberme_cafe](https://www.instagram.com/taiwan_rememberme_cafe/) | Remember Me_記得我·Café | café | 15.1K | 0 | 1 | 1.18 |
| 19 | [@lecinq_cafe](https://www.instagram.com/lecinq_cafe/) |  | café | 15.0K | 0 | 0 | 0.78 |
| 20 | [@coffee_sind](https://www.instagram.com/coffee_sind/) | Coffee Sind | café | 12.5K | 0 | 0 | 0.78 |
| 21 | [@jellyjellytaipei](https://www.instagram.com/jellyjellytaipei/) | JellyJellyCafe | café | 11.7K | 0 | 0 | 0.78 |
| 22 | [@moonshine_coffee](https://www.instagram.com/moonshine_coffee/) | Moonshine Coffee  私釀咖啡 | roastery | 11.4K | 1 | 0 | 0.86 |
| 23 | [@powder_coffee_roasters](https://www.instagram.com/powder_coffee_roasters/) | powder | roastery | 11.2K | 0 | 0 | 0.78 |
| 24 | [@goodman_roaster_taipei](https://www.instagram.com/goodman_roaster_taipei/) | Goodman Roaster Taipei | roastery | 11.2K | 0 | 0 | 0.78 |
| 25 | [@rokucyomecafe](https://www.instagram.com/rokucyomecafe/) | 六丁目 | café | 11.0K | 0 | 0 | 0.78 |
| 26 | [@kaffe_24](https://www.instagram.com/kaffe_24/) | 有kaffe冇 | roastery | 10.9K | 0 | 0 | 0.78 |
| 27 | [@hausinc_cafe](https://www.instagram.com/hausinc_cafe/) | HAUSINC CAFE | café | 10.7K | 0 | 2 | 1.47 |
| 28 | [@thefoxcoffeeclub](https://www.instagram.com/thefoxcoffeeclub/) | THE FOX COFFEE CLUB 🦊 | café | 10.6K | 0 | 0 | 0.78 |
| 29 | [@rufous_coffee_1](https://www.instagram.com/rufous_coffee_1/) | RUFOUS COFFEE ROASTERS | roastery | 10.3K | 0 | 1 | 1.01 |
| 30 | [@instilcoffee](https://www.instagram.com/instilcoffee/) | Instil Coffee | café | 10.0K | 0 | 0 | 0.78 |
| 31 | [@2730.cafe](https://www.instagram.com/2730.cafe/) | 貳柒參零 | café | 9.9K | 0 | 0 | 0.78 |
| 32 | [@fikafikacafe](https://www.instagram.com/fikafikacafe/) | FikaFikaCafe | café | 9.8K | 0 | 0 | 0.78 |
| 33 | [@letoughs_coffee](https://www.instagram.com/letoughs_coffee/) | 人生艱難,櫻花鉤吻鮭 | café | 9.7K | 0 | 0 | 0.78 |
| 34 | [@st1cafe](https://www.instagram.com/st1cafe/) | St.1 cafe | café | 9.6K | 1 | 1 | 0.99 |
| 35 | [@single_origin_espresso_roast](https://www.instagram.com/single_origin_espresso_roast/) | Single Origin espresso & roast | roastery | 9.6K | 0 | 0 | 0.78 |
| 36 | [@alchemist.tw](https://www.instagram.com/alchemist.tw/) | Alchemist | café | 9.5K | 1 | 0 | 0.87 |
| 37 | [@aka.cafe.tw](https://www.instagram.com/aka.cafe.tw/) | AKA Cafe | café | 9.5K | 0 | 0 | 0.78 |
| 38 | [@koshicafetaipei](https://www.instagram.com/koshicafetaipei/) | koshi café | café | 9.5K | 0 | 0 | 0.78 |
| 39 | [@gabee.van_lin](https://www.instagram.com/gabee.van_lin/) | Van Lin | café (barista) | 9.3K | 0 | 1 | 1.45 |
| 40 | [@thefolkstaipei](https://www.instagram.com/thefolkstaipei/) | 𝐓𝐇𝐄 𝐅𝐎𝐋𝐊𝐒 | café | 9.1K | 0 | 0 | 0.78 |
| 41 | [@tomorrow_coffee](https://www.instagram.com/tomorrow_coffee/) | Tomorrow Coffee Roasters | roastery | 9.1K | 0 | 2 | 1.05 |
| 42 | [@whatslife.studio](https://www.instagram.com/whatslife.studio/) | What’s Life Coffee Roaster 山海 | roastery | 9.0K | 0 | 0 | 1.18 |
| 43 | [@greenriver_archive](https://www.instagram.com/greenriver_archive/) | Greenriver Roastery • Archive | roastery | 9.0K | 0 | 0 | 0.78 |
| 44 | [@rufous_coffee_2](https://www.instagram.com/rufous_coffee_2/) | RUFOUS COFFEE ROASTERS 2 | roastery | 8.9K | 0 | 1 | 1.01 |
| 45 | [@d23_coffee](https://www.instagram.com/d23_coffee/) | D23 Coffee | roastery | 8.8K | 0 | 0 | 0.78 |
| 46 | [@peacocks_coffee](https://www.instagram.com/peacocks_coffee/) | PEACOCKS COFFEE | café | 8.7K | 0 | 3 | 1.73 |
| 47 | [@neighborhood_coffee_tw_2022](https://www.instagram.com/neighborhood_coffee_tw_2022/) | 林椐 Neighborhood Coffee Roaster | roastery | 8.7K | 0 | 0 | 0.78 |
| 48 | [@kissa_senmicafe](https://www.instagram.com/kissa_senmicafe/) | 喫茶Sénmi | café | 8.3K | 0 | 1 | 0.89 |
| 49 | [@sumugaga_coffee](https://www.instagram.com/sumugaga_coffee/) | SUMUGAGA COFFEE ROASTERS | roastery | 8.2K | 0 | 2 | 3.09 |
| 50 | [@linsun_cafe](https://www.instagram.com/linsun_cafe/) | 林桑賣咖啡 | roastery (brand) | 8.2K | 0 | 0 | 0.78 |

## Most-endorsed creators (distinct accounts tagging them)

| Account | Name | Followers | # endorsers | Taste | Tagged by |
|---|---|---|---|---|---|
| [@phase_coffee_roasters](https://www.instagram.com/phase_coffee_roasters/) | Phase Coffee Roasters | 20.2K | 11 | 5.92 | crew_coffee.tw, eaglevalleycafe.tw, fuelwood_coffeespace, harryhaodaily_, mushi_co32, neighboring_kaffa, p.coffee_roaster, peakless_coffee_roasters |
| [@erik_liao95](https://www.instagram.com/erik_liao95/) | Erik | 7.3K | 5 | 3.54 | chuyuta, noon.taipei, oasis_coffee_roasters_anhe, oasis_coffee_roasters_nanjing, oasis_coffee_roasting_lab |
| [@coffeestopover](https://www.instagram.com/coffeestopover/) | coffee stopover | 22.7K | 5 | 2.52 | chickengrease1207, coffee_sind, hausinc_cafe, kefipark, sumugaga_coffee |
| [@remedy.by.sip](https://www.instagram.com/remedy.by.sip/) | Remedy select drip bag coffee  | 3.7K | 4 | 2.12 | hausinc_cafe, kefipark, mountaintowncoffeeroasters, sumugaga_coffee |
| [@shallow_cafe](https://www.instagram.com/shallow_cafe/) | SHALLOW CAFE 淺灘咖啡 | 1.1K | 3 | 2.58 | adcafemap_, harryhaodaily_, phase_coffee_roasters |
| [@coffeeimmerse](https://www.instagram.com/coffeeimmerse/) | COFFEE IMMERSE | 2.0K | 3 | 2.04 | coffeeyoutopia, remedy.by.sip, tinytail_daan |
| [@mitsuocoffee](https://www.instagram.com/mitsuocoffee/) | 光生 | 3.8K | 3 | 1.95 | coffeeyoutopia, remedy.by.sip, tinytail_daan |
| [@peacocks_coffee](https://www.instagram.com/peacocks_coffee/) | PEACOCKS COFFEE | 8.7K | 3 | 1.73 | kefipark, remedy.by.sip, sumugaga_coffee |
| [@wenshanroasting1983](https://www.instagram.com/wenshanroasting1983/) | 聞山自家焙煎咖啡館 Wenshan Coffee | 2.5K | 3 | 1.69 | rufous_coffee_1, rufous_coffee_2, tenpastten.coffee |
| [@billy_roaster](https://www.instagram.com/billy_roaster/) | Billy Roaster | 5.0K | 3 | 1.23 | fuelwood_coffeespace, harryhaodaily_, phase_coffee_roasters |
| [@kite_coffee_](https://www.instagram.com/kite_coffee_/) | K I T E   C O F F E E | 7.6K | 3 | 1.09 | coffeeyoutopia, harryhaodaily_, phase_coffee_roasters |
| [@sumugaga_coffee](https://www.instagram.com/sumugaga_coffee/) | SUMUGAGA COFFEE ROASTERS | 8.2K | 2 | 3.09 | coffeestopover, kefipark |
| [@hausinc_cafe](https://www.instagram.com/hausinc_cafe/) | HAUSINC CAFE | 10.7K | 2 | 1.47 | kefipark, sumugaga_coffee |
| [@tenpastten.coffee](https://www.instagram.com/tenpastten.coffee/) | TEN PAST TEN COFFEE ROASTERS | 1.1K | 2 | 1.47 | rufous_coffee_1, rufous_coffee_2 |
| [@ala.arena_212](https://www.instagram.com/ala.arena_212/) | 水試所    Coffee•Matcha•Dessert | 0.5K | 2 | 1.47 | coffeeunderwater, cuw.eric |
| [@noon.taipei](https://www.instagram.com/noon.taipei/) | n o o n | 16.7K | 2 | 1.43 | erik_liao95, harryhaodaily_ |
| [@tomorrow_coffee](https://www.instagram.com/tomorrow_coffee/) | Tomorrow Coffee Roasters | 9.1K | 2 | 1.05 | coffee_sind, kissa_senmicafe |
| [@yiyi.taipei](https://www.instagram.com/yiyi.taipei/) | 液 藝  Y i Y i | 6.7K | 2 | 1.01 | harryhaodaily_, phase_coffee_roasters |
| [@enroute_coffee](https://www.instagram.com/enroute_coffee/) | 引路咖啡 | 6.4K | 2 | 1.01 | harryhaodaily_, phase_coffee_roasters |
| [@p.coffee_roaster](https://www.instagram.com/p.coffee_roaster/) | P.COFFEE ROASTER | 3.2K | 2 | 1.01 | harryhaodaily_, phase_coffee_roasters |

## Food bloggers & curators by followers (28 total)

| # | Account | Name | Followers | Makers tagged | Taste |
|---|---|---|---|---|---|
| 1 | [@4foodie](https://www.instagram.com/4foodie/) | 4foodie美食分享｜餐飲行銷 ｜社群代操 | 736K | 0 | 0.00 |
| 2 | [@al.dente.life](https://www.instagram.com/al.dente.life/) | al.dente.life | 436K | 0 | 0.00 |
| 3 | [@tatlertaiwan](https://www.instagram.com/tatlertaiwan/) | Tatler Taiwan *(media/curator)* | 360K | 0 | 0.00 |
| 4 | [@bellataiwan](https://www.instagram.com/bellataiwan/) | BellaTaiwan / Bella儂儂 *(media/curator)* | 274K | 0 | 0.00 |
| 5 | [@47_food.life](https://www.instagram.com/47_food.life/) | 47食樂天地| 美食旅遊 台北 台中 桃園 國外| LEE,SHIH | 250K | 0 | 0.00 |
| 6 | [@taipeifoodie](https://www.instagram.com/taipeifoodie/) | Taipei Foodie | 155K | 0 | 0.00 |
| 7 | [@adcafe_](https://www.instagram.com/adcafe_/) | AD Cafe｜咖啡知識☕️店家推薦📸 | 148K | 0 | 0.00 |
| 8 | [@hungryintaipei](https://www.instagram.com/hungryintaipei/) | Joan | 66.4K | 0 | 0.00 |
| 9 | [@taipeieater](https://www.instagram.com/taipeieater/) | CHARLENE YANG | TAIPEIEATER 🇹🇼 | 61.3K | 0 | 0.00 |
| 10 | [@stylemastermag](https://www.instagram.com/stylemastermag/) | style master Taiwan型格誌 *(media/curator)* | 40.4K | 0 | 0.00 |
| 11 | [@zero.dailynotes](https://www.instagram.com/zero.dailynotes/) | 凱倫吃貨日常｜台北、新北美食 | 36.8K | 0 | 0.00 |
| 12 | [@duringmyjourney](https://www.instagram.com/duringmyjourney/) | 我的旅圖中during my journey | 18.9K | 0 | 0.00 |
| 13 | [@futhefoodie](https://www.instagram.com/futhefoodie/) | JEN | FOOD LOVER | 12.1K | 0 | 0.00 |
| 14 | [@sandy_eat](https://www.instagram.com/sandy_eat/) | 仙蒂食-台北美食、新北美食、台中美食、高雄美食🍴 | 11.2K | 0 | 0.00 |
| 15 | [@coffeeyoutopia](https://www.instagram.com/coffeeyoutopia/) | Brian | 咖啡廳日常指南•台北 新北 桃園 | 10.4K | 7 | 4.75 |
| 16 | [@master_of_foodie](https://www.instagram.com/master_of_foodie/) | 美食研究生-真真| 台北 新北 美食 | 分享 | 6.5K | 0 | 0.00 |
| 17 | [@wonder4.gourmet](https://www.instagram.com/wonder4.gourmet/) | Jason Liu的食界奇觀 - 在踩雷與摘星之間 | 6.5K | 0 | 0.00 |
| 18 | [@latte7119](https://www.instagram.com/latte7119/) | latte Li 🇹🇼 | 5.0K | 0 | 0.00 |
| 19 | [@adcafemap_](https://www.instagram.com/adcafemap_/) | AD 咖啡圈｜你的咖啡生活嚮導 | 4.6K | 1 | 1.58 |
| 20 | [@angelababy_0218](https://www.instagram.com/angelababy_0218/) | 梅格（Angelababy）享樂日記 | 4.4K | 0 | 0.00 |
| 21 | [@harryhaodaily_](https://www.instagram.com/harryhaodaily_/) | 牧羊人的日記🐺 | 4.1K | 22 | 25.21 |
| 22 | [@gur.room](https://www.instagram.com/gur.room/) | 灶室  gur room | 4.0K | 0 | 0.00 |
| 23 | [@eatingintaipei](https://www.instagram.com/eatingintaipei/) | Eating in Taipei | 3.1K | 0 | 0.00 |
| 24 | [@_ss.127_](https://www.instagram.com/_ss.127_/) | 𝑺𝒉𝒊𝒂𝒏𝒈 | 2.8K | 0 | 0.00 |
| 25 | [@salihahalin](https://www.instagram.com/salihahalin/) | 莎莉哈 | 2.5K | 0 | 0.00 |
| 26 | [@icey_lovelife](https://www.instagram.com/icey_lovelife/) | 食攝人生｜咖啡探店｜日本慢旅 | 1.6K | 0 | 0.00 |
| 27 | [@piggeeats](https://www.instagram.com/piggeeats/) | pigg-e-eats 🇹🇼🇺🇸🌎 | 1.0K | 0 | 0.00 |
| 28 | [@whostalking_0208](https://www.instagram.com/whostalking_0208/) | whostalking胡說｜美食、咖啡、說故事 | 0.2K | 0 | 0.00 |
