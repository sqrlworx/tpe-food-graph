# Taiwan food creators × food bloggers (Instagram)

Interactive graph: `index.html` (open in a browser; click a node to see who tagged it).
Full data: `food_creators.csv`, `food_bloggers.csv`, `graph.json`.

**Edge A → B** = A tagged / @mentioned / co-posted with B in one of A's 12 most recent posts.
Links between affiliated accounts (sister shops, an owner tagging their own shop) are excluded.
**Bloggers / Makers** = how many distinct food bloggers / food makers tagged the account.
**Taste (creators)** = PageRank over the endorsement graph (1.0 = average).
**Taste (bloggers)** = Σ over makers they tag of log₂(1 + other accounts that also tagged that maker).

## Top 50 food creators by followers (173 total)

| # | Account | Name | Type | Followers | Tagged by bloggers | Tagged by makers | Taste |
|---|---|---|---|---|---|---|---|
| 1 | [@_eddy_wang_](https://www.instagram.com/_eddy_wang_/) | Eddy Wang | bakery | 155K | 0 | 2 | 1.30 |
| 2 | [@hsiao.yen_](https://www.instagram.com/hsiao.yen_/) | H.YEN 可頌專賣店 | bakery | 81.9K | 0 | 1 | 0.48 |
| 3 | [@quelques_p](https://www.instagram.com/quelques_p/) | 某某-Quelques Patisseries | dessert | 69.6K | 1 | 0 | 0.49 |
| 4 | [@minimal_gelato](https://www.instagram.com/minimal_gelato/) | MINIMAL | dessert | 65.7K | 1 | 0 | 3.41 |
| 5 | [@wuniquetaipei](https://www.instagram.com/wuniquetaipei/) | WUnique Pâtisserie | dessert | 64.2K | 0 | 0 | 2.86 |
| 6 | [@but.we.love.butter](https://www.instagram.com/but.we.love.butter/) | but. we love butter | dessert | 63.7K | 0 | 0 | 0.43 |
| 7 | [@petitchouxx18](https://www.instagram.com/petitchouxx18/) | PETIT CHOU  PÂTISSERIE | dessert | 48.9K | 0 | 1 | 0.82 |
| 8 | [@lerubanpatisserie](https://www.instagram.com/lerubanpatisserie/) | 法朋烘焙甜點坊 | dessert | 46.2K | 1 | 0 | 3.65 |
| 9 | [@weekendnodessert](https://www.instagram.com/weekendnodessert/) | WeekendnoDessert | dessert | 44.4K | 0 | 0 | 0.43 |
| 10 | [@celebread.acs](https://www.instagram.com/celebread.acs/) | CELEBREAD 安和店 | bakery | 39.9K | 2 | 0 | 1.35 |
| 11 | [@her_her_studio](https://www.instagram.com/her_her_studio/) | Her x Her 台中蛋糕·烘焙教學·海外烘焙遊學團 | dessert | 39.0K | 0 | 5 | 2.32 |
| 12 | [@minuit1200](https://www.instagram.com/minuit1200/) | 深夜裡的法國手工甜點 | 台北忠孝復興・法式塔類甜點・節日送 | dessert | 38.6K | 0 | 1 | 0.81 |
| 13 | [@_moon_baking](https://www.instagram.com/_moon_baking/) | Moon Baking Studio | bakery | 37.7K | 0 | 0 | 0.43 |
| 14 | [@feedthewife](https://www.instagram.com/feedthewife/) | 胖死我太太烘焙坊 Feed The Wife Bakery  | bakery | 37.4K | 0 | 0 | 0.43 |
| 15 | [@woowoo_hi](https://www.instagram.com/woowoo_hi/) | 窩巷 Hidden Lane ®｜台中甜點 水果蛋糕 | dessert | 36.8K | 0 | 1 | 0.63 |
| 16 | [@chimori_seika](https://www.instagram.com/chimori_seika/) | 千森製菓ちもり-台南甜點咖啡 | dessert | 31.5K | 0 | 0 | 0.43 |
| 17 | [@habibipatisserie](https://www.instagram.com/habibipatisserie/) | Habibi Pâtisserie | dessert | 29.3K | 0 | 0 | 0.43 |
| 18 | [@egghost_dessert](https://www.instagram.com/egghost_dessert/) | 疍宅 | dessert | 29.3K | 0 | 0 | 0.43 |
| 19 | [@crem_tw](https://www.instagram.com/crem_tw/) | CRÈM 奶油_甜點專門店 | dessert | 29.0K | 0 | 0 | 0.43 |
| 20 | [@aufglet](https://www.instagram.com/aufglet/) | AUFGLET | bakery | 28.5K | 0 | 0 | 0.43 |
| 21 | [@libreadry](https://www.instagram.com/libreadry/) | libreadry 巢屋  |  自家製酵母麵包 | bakery | 28.0K | 0 | 0 | 0.43 |
| 22 | [@aichi7777](https://www.instagram.com/aichi7777/) | 愛柒Ai Chi | dessert | 28.0K | 3 | 0 | 1.11 |
| 23 | [@le_beret_bleu](https://www.instagram.com/le_beret_bleu/) | 藍色貝蕾 | bakery | 27.1K | 0 | 0 | 0.43 |
| 24 | [@theslice.shop](https://www.instagram.com/theslice.shop/) | The Slice Shop | other | 26.6K | 2 | 0 | 1.14 |
| 25 | [@pangolin.pain](https://www.instagram.com/pangolin.pain/) | Boulangerie Pangolin・麵包林里 | bakery | 26.2K | 0 | 0 | 0.43 |
| 26 | [@biyue_dessert](https://www.instagram.com/biyue_dessert/) | 碧月Dessert | dessert | 26.1K | 1 | 0 | 0.58 |
| 27 | [@kure8kombucha](https://www.instagram.com/kure8kombucha/) | KURE8 | 8酵茶 | other | 26.0K | 0 | 1 | 1.30 |
| 28 | [@cestcest_patisseries](https://www.instagram.com/cestcest_patisseries/) | C’EST C’EST PÂTISSERIES | dessert | 25.2K | 0 | 0 | 1.10 |
| 29 | [@yu_chocolatier](https://www.instagram.com/yu_chocolatier/) | Yu Chocolatier 畬室 巧克力 | dessert | 25.1K | 2 | 0 | 1.03 |
| 30 | [@vnvpatisserie](https://www.instagram.com/vnvpatisserie/) | VNV Pâtisserie et Chocolaterie | dessert | 24.3K | 0 | 1 | 0.79 |
| 31 | [@flowerdessert_taichung](https://www.instagram.com/flowerdessert_taichung/) | 花甜囍室 Flowerdessert Coffee Roas | dessert | 22.3K | 0 | 0 | 0.43 |
| 32 | [@manomano__77](https://www.instagram.com/manomano__77/) | MANO MANO DESSERT | dessert | 21.7K | 1 | 0 | 0.49 |
| 33 | [@leavenworkshop](https://www.instagram.com/leavenworkshop/) | 璞家工作室 Leaven workshop | bakery | 20.6K | 1 | 0 | 0.83 |
| 34 | [@lilinli_tw](https://www.instagram.com/lilinli_tw/) | 栗林裏 Li Lin Li | dessert | 20.4K | 1 | 0 | 8.77 |
| 35 | [@shiyu.patisserie](https://www.instagram.com/shiyu.patisserie/) | 偲雪日法甜點｜シユ｜ shiyu | dessert | 20.0K | 0 | 1 | 0.63 |
| 36 | [@albuca_dessert](https://www.instagram.com/albuca_dessert/) | 植物園烘焙甜點店 Albuca Dessert | dessert | 20.0K | 0 | 0 | 0.43 |
| 37 | [@iminding_story](https://www.instagram.com/iminding_story/) | 獻烘焙 iminding 可頌專門店 | bakery | 19.8K | 0 | 1 | 0.48 |
| 38 | [@qundao_kitchen](https://www.instagram.com/qundao_kitchen/) | 群島李季｜廚房裡的日常 | bakery | 19.4K | 1 | 1 | 0.82 |
| 39 | [@chuan_tung](https://www.instagram.com/chuan_tung/) | 全統西點麵包CHUAN TUNG | bakery | 18.5K | 0 | 2 | 0.63 |
| 40 | [@studiodudoublev](https://www.instagram.com/studiodudoublev/) | Double V | dessert | 17.5K | 3 | 4 | 2.51 |
| 41 | [@syrupless](https://www.instagram.com/syrupless/) | SyrupLess稍甜 | dessert | 17.5K | 0 | 0 | 0.43 |
| 42 | [@fourninetine_bakery](https://www.instagram.com/fourninetine_bakery/) | Fourninetine Bakery | bakery | 17.3K | 0 | 0 | 0.43 |
| 43 | [@okashi_kau](https://www.instagram.com/okashi_kau/) | 御菓子花雨 | dessert | 16.9K | 1 | 1 | 3.58 |
| 44 | [@lemoncia_tw](https://www.instagram.com/lemoncia_tw/) | 花鳥川 | dessert | 16.4K | 1 | 0 | 0.45 |
| 45 | [@heritagetaipei](https://www.instagram.com/heritagetaipei/) | Heritage Bakery & Cafe | bakery | 16.2K | 2 | 0 | 1.38 |
| 46 | [@pain.goodbaking](https://www.instagram.com/pain.goodbaking/) | 邦穀烘焙製造所 | bakery | 15.9K | 0 | 0 | 0.43 |
| 47 | [@wheat_allergy_bakingstudio](https://www.instagram.com/wheat_allergy_bakingstudio/) | 小  麥  過  敏 | bakery | 15.7K | 2 | 3 | 1.14 |
| 48 | [@risebakery.taipei](https://www.instagram.com/risebakery.taipei/) | Rise Bakery | bakery | 15.3K | 0 | 0 | 0.43 |
| 49 | [@chocolatmurmur](https://www.instagram.com/chocolatmurmur/) | 林庚辰｜巧克力碎碎唸 | dessert (chef) | 15.2K | 0 | 1 | 3.47 |
| 50 | [@purebreadbakery](https://www.instagram.com/purebreadbakery/) | Purebread Bakery | bakery | 15.1K | 0 | 0 | 0.43 |

## Most-endorsed creators (distinct accounts tagging them)

| Account | Name | Followers | # endorsers | Taste | Tagged by |
|---|---|---|---|---|---|
| [@studiodudoublev](https://www.instagram.com/studiodudoublev/) | Double V | 17.5K | 8 | 2.51 | chin_feng_bee_farm, chine_hsuan, deuxdouxcremerie, eatingintaipei, fa__burger, kure8kombucha, peray_blog, vanessafoodies |
| [@chin_feng_bee_farm](https://www.instagram.com/chin_feng_bee_farm/) | 沁峯養蜂場 | 2.5K | 6 | 3.22 | 8818pizzahouse, _eddy_wang_, chine_hsuan, peray_blog, studiodudoublev, zhan_humor |
| [@her_her_studio](https://www.instagram.com/her_her_studio/) | Her x Her 台中蛋糕·烘焙教學·海外烘焙遊學團 | 39.0K | 5 | 2.32 | 4boitubake, anywaydessert, blue_zuo, petitchouxx18, shiyu.patisserie |
| [@wheat_allergy_bakingstudio](https://www.instagram.com/wheat_allergy_bakingstudio/) | 小  麥  過  敏 | 15.7K | 5 | 1.14 | 4boitubake, her_her_studio, peng_chieh_wang, ryan.keelung, wubread_nofat |
| [@celebread.acs](https://www.instagram.com/celebread.acs/) | CELEBREAD 安和店 | 39.9K | 4 | 1.35 | fa__burger, ryan.keelung, tau_ga_mma, wubread_nofat |
| [@_eddy_wang_](https://www.instagram.com/_eddy_wang_/) | Eddy Wang | 155K | 4 | 1.30 | 8818pizzahouse, chin_feng_bee_farm, onlivefm8818, studiodudoublev |
| [@renxren2.0](https://www.instagram.com/renxren2.0/) | 人x人 2.0 | 4.3K | 4 | 0.83 | fudge_faqi, lasfera_boulangerie, nowchance_xd, peacepiece_bakery |
| [@lerubanpatisserie](https://www.instagram.com/lerubanpatisserie/) | 法朋烘焙甜點坊 | 46.2K | 3 | 3.65 | tatlerdiningtw, tien_feng, tsujiri_tw |
| [@majo_majo_bakery](https://www.instagram.com/majo_majo_bakery/) | 花磚裏 （找到了可頌羅東店） | 2.5K | 3 | 3.26 | 4boitubake, found_croissanter, ryan.keelung |
| [@wujinpatisserie](https://www.instagram.com/wujinpatisserie/) | 霧金甜點｜台北甜點·費南雪 | 0.3K | 3 | 2.10 | alex__pastrychef, bouffetw, ryan.keelung |
| [@ms.fupo](https://www.instagram.com/ms.fupo/) | 富婆醬 FUPO! Sauce | 4.6K | 3 | 1.71 | taipeieater, tomuwine, urbantree.tw |
| [@theslice.shop](https://www.instagram.com/theslice.shop/) | The Slice Shop | 26.6K | 3 | 1.14 | eatingintaipei, ericedits_, wubread_nofat |
| [@aichi7777](https://www.instagram.com/aichi7777/) | 愛柒Ai Chi | 28.0K | 3 | 1.11 | chensongeat_, eatha.foodie, hanyu_912 |
| [@cestcest_patisseries](https://www.instagram.com/cestcest_patisseries/) | C’EST C’EST PÂTISSERIES | 25.2K | 3 | 1.10 | azulejo_2f, muguet.street, phase_coffee_roasters |
| [@peng_chieh_wang](https://www.instagram.com/peng_chieh_wang/) | Jay Wang 王鵬傑 | 3.8K | 3 | 0.97 | katsumi_wu, shakespeare2010.co, wubread_nofat |
| [@vb.bakery](https://www.instagram.com/vb.bakery/) | Vanessa's Bakery 凡內莎烘焙工作室 | 4.4K | 3 | 0.95 | 4boitubake, chiayin85, pipeline.pain |
| [@pipeline.pain](https://www.instagram.com/pipeline.pain/) | PIPELINE派不賴 | 3.8K | 3 | 0.86 | 4boitubake, chiayin85, vb.bakery |
| [@missvbakery](https://www.instagram.com/missvbakery/) | Miss V Bakery | 14.2K | 3 | 0.62 | 4boitubake, lasfera_boulangerie, renxren2.0 |
| [@lilinli_tw](https://www.instagram.com/lilinli_tw/) | 栗林裏 Li Lin Li | 20.4K | 2 | 8.77 | chen_yuan_hao, hi.sydney |
| [@okashi_kau](https://www.instagram.com/okashi_kau/) | 御菓子花雨 | 16.9K | 2 | 3.58 | chocolatmurmur, flavornews.tw |

## Food bloggers & curators by followers (72 total)

| # | Account | Name | Followers | Makers tagged | Taste |
|---|---|---|---|---|---|
| 1 | [@4foodie](https://www.instagram.com/4foodie/) | 4foodie美食分享｜餐飲行銷 ｜社群代操 | 736K | 0 | 0.00 |
| 2 | [@popyummy_mag](https://www.instagram.com/popyummy_mag/) | PopYummy 波波發胖 *(media/curator)* | 557K | 0 | 0.00 |
| 3 | [@eatha.foodie](https://www.instagram.com/eatha.foodie/) | 台中美食 吃吃霞/台北 台南 全台美食 日常分享 | 455K | 1 | 1.58 |
| 4 | [@al.dente.life](https://www.instagram.com/al.dente.life/) | al.dente.life | 436K | 1 | 0.00 |
| 5 | [@twopigs_travel_food](https://www.instagram.com/twopigs_travel_food/) | 兩個豬女孩旅遊食記🐷台北 台中 高雄 台南美食 食譜分享 | 423K | 0 | 0.00 |
| 6 | [@twoboysfoods](https://www.instagram.com/twoboysfoods/) | 兩個男孩日常食記👬台中 台南 台北 彰化 美食 | 320K | 0 | 0.00 |
| 7 | [@foodtaichung_teddy](https://www.instagram.com/foodtaichung_teddy/) | Teddy泰迪 台中美食 Chen, Tai-Cheng | 295K | 0 | 0.00 |
| 8 | [@chensongeat_](https://www.instagram.com/chensongeat_/) | 🇹🇼Song吃喝玩樂日常‼台中 台南 桃園 彰化 台北 | 256K | 1 | 1.58 |
| 9 | [@hua.dh](https://www.instagram.com/hua.dh/) | 冬冬🌸生活美食日記｜台北 台中 桃園 高雄 台南 母嬰 美食 旅遊  | 250K | 0 | 0.00 |
| 10 | [@47_food.life](https://www.instagram.com/47_food.life/) | 47食樂天地| 美食旅遊 台北 台中 桃園 國外| LEE,SHIH | 249K | 0 | 0.00 |
| 11 | [@foodietaichung__leaf](https://www.instagram.com/foodietaichung__leaf/) | 凱開｜台中美食 台北/台南/韓國旅遊 | 227K | 0 | 0.00 |
| 12 | [@hanyu_912](https://www.instagram.com/hanyu_912/) | 🍉玉玉の日々🍉食&旅.台中美食.全台小吃 | 218K | 1 | 1.58 |
| 13 | [@tainanxian_food](https://www.instagram.com/tainanxian_food/) | 台南小白💜 台南美食‧高雄‧嘉義‧出國旅遊 | 197K | 0 | 0.00 |
| 14 | [@phoebe_foodaily](https://www.instagram.com/phoebe_foodaily/) | 菲比的食物日常•台北 桃園 台中 美食 YU-PING,LIN | 191K | 0 | 0.00 |
| 15 | [@bnbnlovefood](https://www.instagram.com/bnbnlovefood/) | 奔奔小姐🎀旅遊・美食・親子｜Chen Ke-Ying | 163K | 0 | 0.00 |
| 16 | [@taipeifoodie](https://www.instagram.com/taipeifoodie/) | Taipei Foodie | 155K | 0 | 0.00 |
| 17 | [@amos0716](https://www.instagram.com/amos0716/) | 艾瑪斯｜美食 × 旅遊 × 住宿 × 景點 × 影像創作者 | 153K | 1 | 0.00 |
| 18 | [@demi.now](https://www.instagram.com/demi.now/) | 黛咪 。人生大事，吃喝二字 🇹🇼 | 149K | 0 | 0.00 |
| 19 | [@adcafe_](https://www.instagram.com/adcafe_/) | AD Cafe｜咖啡知識☕️店家推薦📸 | 147K | 0 | 0.00 |
| 20 | [@iamirenesu](https://www.instagram.com/iamirenesu/) | 愛吃SUSU!! 台中 台北 高雄 日韓 美食旅遊 | 139K | 1 | 0.00 |
| 21 | [@07vanessa18](https://www.instagram.com/07vanessa18/) | 台中美食✨Wu是巫婆ㄉ巫˙𐃷˙ | 119K | 0 | 0.00 |
| 22 | [@bearyangfan](https://www.instagram.com/bearyangfan/) | ❤️Amber Young❤️ | 110K | 0 | 0.00 |
| 23 | [@h_a_n.7](https://www.instagram.com/h_a_n.7/) | Sammy山米 | 103K | 0 | 0.00 |
| 24 | [@foodie.taiwan](https://www.instagram.com/foodie.taiwan/) | Foodie Taiwan | 台北美食 | 台灣美食 | 94.7K | 0 | 0.00 |
| 25 | [@mr.xx_yumyum](https://www.instagram.com/mr.xx_yumyum/) | 魚丸日常食旅｜台中美食 彰化美食 台北美食 台南美食 | 92.0K | 1 | 0.00 |
| 26 | [@selftaughtgourmet](https://www.instagram.com/selftaughtgourmet/) | 美食家的自學之路 Self-taught Gourmet | 88.6K | 1 | 1.00 |
| 27 | [@t.b_foodie](https://www.instagram.com/t.b_foodie/) | TB Foodie | 米其林 | 質感美食 | CSH | 84.7K | 1 | 0.00 |
| 28 | [@tatlerdiningtw](https://www.instagram.com/tatlerdiningtw/) | Tatler Dining Taiwan *(media/curator)* | 67.3K | 6 | 3.58 |
| 29 | [@hungryintaipei](https://www.instagram.com/hungryintaipei/) | Joan | 66.4K | 2 | 1.00 |
| 30 | [@_bw.photo_h](https://www.instagram.com/_bw.photo_h/) | 柏維-全台｜住宿.旅遊.美食.攝影 | 66.1K | 0 | 0.00 |
| 31 | [@taipeieats](https://www.instagram.com/taipeieats/) | TAIPEI  EATS | 63.8K | 0 | 0.00 |
| 32 | [@taipeieater](https://www.instagram.com/taipeieater/) | CHARLENE YANG | TAIPEIEATER 🇹🇼 | 61.3K | 4 | 2.58 |
| 33 | [@foodlemaps](https://www.instagram.com/foodlemaps/) | Foodle Maps 台北美食 台灣美食 住宿分享 | 60.4K | 0 | 0.00 |
| 34 | [@chefdinnerplan](https://www.instagram.com/chefdinnerplan/) | 王俊之 | 57.7K | 0 | 0.00 |
| 35 | [@ducky_eat_](https://www.instagram.com/ducky_eat_/) | 🦆短腿小鴨｜旅遊&美食 | 54.7K | 1 | 0.00 |
| 36 | [@albee033880](https://www.instagram.com/albee033880/) | 愛比妞 台南/台北美食 | 53.2K | 0 | 0.00 |
| 37 | [@maomao_eat_ramen](https://www.instagram.com/maomao_eat_ramen/) | 拉麵毛Mao 美食攻略集 | 台灣日本全紀錄 | 46.9K | 0 | 0.00 |
| 38 | [@jack_food_diary](https://www.instagram.com/jack_food_diary/) | 傑克｜竹北美食 / 新竹美食 / 全台住宿開箱 | 43.7K | 0 | 0.00 |
| 39 | [@flavornews.tw](https://www.instagram.com/flavornews.tw/) | Flavor 風格美食指南 *(media/curator)* | 39.8K | 6 | 1.00 |
| 40 | [@zero.dailynotes](https://www.instagram.com/zero.dailynotes/) | 凱倫吃貨日常｜台北、新北美食 | 36.6K | 0 | 0.00 |
| 41 | [@taberu.food](https://www.instagram.com/taberu.food/) | 肉依 美食旅遊生活分享 ✿ | 36.4K | 0 | 0.00 |
| 42 | [@1ggfood](https://www.instagram.com/1ggfood/) | 蛋談美食 | 36.0K | 0 | 0.00 |
| 43 | [@hi.sydney](https://www.instagram.com/hi.sydney/) | 郭 雪梨 | 35.3K | 1 | 1.00 |
| 44 | [@applespoon](https://www.instagram.com/applespoon/) | Ying C. 陳穎 | 33.2K | 4 | 1.00 |
| 45 | [@500dishes_tw](https://www.instagram.com/500dishes_tw/) | 500盤 *(media/curator)* | 28.0K | 0 | 0.00 |
| 46 | [@haokoufu](https://www.instagram.com/haokoufu/) | HY Cathy Ho | Curator of HaoKouFu | 28.0K | 0 | 0.00 |
| 47 | [@vanessafoodies](https://www.instagram.com/vanessafoodies/) | VanessaFoodies | 24.3K | 5 | 4.00 |
| 48 | [@_bs.foodie](https://www.instagram.com/_bs.foodie/) | 柏食客/ 𝘻𝘦𝘯丨台北•台中•宜蘭•桃園美食·住宿·咖啡廳·景點 | 24.2K | 0 | 0.00 |
| 49 | [@4foodie.luxe](https://www.instagram.com/4foodie.luxe/) | 4foodie Luxe 精緻料理 米其林餐廳推薦 Fine Din | 19.5K | 0 | 0.00 |
| 50 | [@hungry2_1016](https://www.instagram.com/hungry2_1016/) | 🥢餓餓🥢♤ 美食 | 旅遊 | 生活 | 景點 ♤ | 17.0K | 0 | 0.00 |
| 51 | [@melvinyang1106](https://www.instagram.com/melvinyang1106/) | Melvin 梅爾文｜住宿、旅遊、美食、開箱 | 16.5K | 0 | 0.00 |
| 52 | [@foodgasmic_tw](https://www.instagram.com/foodgasmic_tw/) | foodgasmic 美食高潮 *(media/curator)* | 16.2K | 0 | 0.00 |
| 53 | [@uj85_](https://www.instagram.com/uj85_/) | 注音符號のㄩㄐ 🥟 | 12.8K | 0 | 0.00 |
| 54 | [@futhefoodie](https://www.instagram.com/futhefoodie/) | JEN | FOOD LOVER | 12.1K | 0 | 0.00 |
| 55 | [@_place_for_eating](https://www.instagram.com/_place_for_eating/) | 高雄、台南、嘉義美食 /選物店/展覽/旅行/生活 小肥鼠 | 11.5K | 0 | 0.00 |
| 56 | [@bonpainfair](https://www.instagram.com/bonpainfair/) | Bon Pain 麵包祭 *(media/curator)* | 9.8K | 0 | 0.00 |
| 57 | [@peray_blog](https://www.instagram.com/peray_blog/) | Peray | 8.7K | 3 | 6.58 |
| 58 | [@looking4goodfood](https://www.instagram.com/looking4goodfood/) | 雷的餐廳名單X高雄/台北/香港/日本 | 8.3K | 0 | 0.00 |
| 59 | [@foodmap_hktw](https://www.instagram.com/foodmap_hktw/) | Foodmap//🇹🇼台中美食🇭🇰香港美食 | 7.3K | 0 | 0.00 |
| 60 | [@ryan.keelung](https://www.instagram.com/ryan.keelung/) | 萊恩RYAN KEELUNG | 7.1K | 6 | 8.49 |
| 61 | [@rj_uice_at](https://www.instagram.com/rj_uice_at/) | 銅茂凱 | 6.9K | 3 | 1.00 |
| 62 | [@bonnie.eat](https://www.instagram.com/bonnie.eat/) | 飽泥吃吃 | 6.1K | 0 | 0.00 |
| 63 | [@olga.nanaco](https://www.instagram.com/olga.nanaco/) | Olga Huang | 6.0K | 0 | 0.00 |
| 64 | [@foodwithme.22](https://www.instagram.com/foodwithme.22/) | 犬の食楽記 🍽彰化 員林 台中 | 5.1K | 0 | 0.00 |
| 65 | [@joanne._1005](https://www.instagram.com/joanne._1005/) | 林林ㄦ🧸 | 5.1K | 0 | 0.00 |
| 66 | [@bofoodiecheckin_10](https://www.instagram.com/bofoodiecheckin_10/) |  | 4.1K | 0 | 0.00 |
| 67 | [@wubread_nofat](https://www.instagram.com/wubread_nofat/) | 吾胖 WU Bread｜烘焙知識轉譯｜用白話文說麵包 | 3.3K | 11 | 9.49 |
| 68 | [@eatingintaipei](https://www.instagram.com/eatingintaipei/) | Eating in Taipei | 3.1K | 2 | 4.58 |
| 69 | [@lesliewangart](https://www.instagram.com/lesliewangart/) | Leslie Wang 王意馨 ｜ Food Culture Art | 1.4K | 1 | 1.00 |
| 70 | [@we77123](https://www.instagram.com/we77123/) | 周北極 | 1.4K | 0 | 0.00 |
| 71 | [@eatboom.foodie](https://www.instagram.com/eatboom.foodie/) | 飯局芃友｜高雄美食·屏東美食·平價餐廳·甜點午茶 | 0.7K | 1 | 0.00 |
| 72 | [@vcd189](https://www.instagram.com/vcd189/) | 施施 | 0.1K | 4 | 0.00 |
