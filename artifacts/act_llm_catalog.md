<!-- AUTO-GENERATED from act_taxonomy.ttl by generate_artifacts.py on 2026-10-03. DO NOT EDIT BY HAND. Edit the TTL and re-run. -->

# ACT ActionType Catalog (for LLM classification)

Compact list of ActionTypes with representative vocabulary, for use in classifier prompts.

## Operational notes

- MULTILABEL: A separate resource (act_multilabel.ttl) records expressions that map to more than one ActionType. Multilabel is NOT expressed via skos:broader here (broader is reserved for the category hierarchy).
- AFFIX NORMALIZATION RULES (type-level): 〜開始 => {head-class, Beginning} multilabel; 〜化 => Transformation by default; 再〜 => {stem-class, Repetition} multilabel; use Revival only when stem itself denotes restoration (復活・回復・再興); light verbs (する/なる/おく/うける) => General.
- KNOWN LIMITATION: This is a context-independent, type-level dictionary. Agent/Theme-dependent boundary cases (e.g. 派遣 Military vs Diplomatic) have no single type-level answer by design.
- PROVISIONAL ITEMS: Authorization internal split (interpersonal vs institutional); CulturalExpression future split into CulturalProduction / ReligiousPractice (threshold n>=10); modern-era vocabulary gap (e.g. 打ち上げ).

## 軍事・暴力・抑圧 / Military, Violence & Suppression

- **AssassinationMassacre** (暗殺・虐殺 / Assassination Massacre): JA: 暗殺・爆殺・射殺・虐殺・粛清・殺害・毒殺・殺戮 | EN: assassinate, massacre, purge
- **CaptureAndPunishment** (拘束・処罰 / Capture And Punishment): JA: 逮捕・捕縛・拉致・配流・処刑・斬首・刑死・捕囚・監禁 | EN: arrest, imprison, execute, exile
- **ConquestOccupation** (征服・占領 / Conquest Occupation): JA: 征服・占領・占拠・制圧・支配・領有・支配下におく・駐留 | EN: conquer, occupy, annex
- **Defeat** (敗北・降伏 / Defeat): JA: 敗北・大敗・惨敗・降伏・投降・撤退・敗走 | EN: defeat, surrender, retreat
- **DisputeConflict** (紛争・衝突 / Dispute Conflict): JA: 衝突・抗争・参戦・内戦・交戦・武力衝突・戦闘・戦争 | EN: clash, war, civil war, combat
- **MilitaryAttack** (軍事攻撃 / Military Attack): JA: 攻撃・侵攻・侵入・包囲・攻略・撃退・進軍・出兵・上陸・進出 | EN: attack, invade, besiege, advance
- **Subjugation** (服属・臣従 / Subjugation): JA: 服属・臣従する・支配下に入る・服従・帰順 | EN: submit, become a vassal
- **Suppression** (弾圧・抑圧 / Suppression): JA: 弾圧・鎮圧・迫害・排除・禁止・布教禁止・非合法化 | EN: suppress, persecute, ban
- **Victory** (勝利 / Victory): JA: 勝利・大勝・平定・撃破・完勝・戦勝 | EN: victory, triumph, rout

## 集団抵抗・反乱 / Collective Resistance & Revolt

- **ResistanceProtest** (抵抗・抗議 / Resistance Protest): JA: 抵抗・抗議・反対・ボイコット・デモ・批判・請願・独立運動 | EN: resist, protest, boycott, petition
- **RevoltInsurrection** (反乱・革命 / Revolt Insurrection): JA: 反乱・蜂起・一揆・暴動・革命・クーデター・挙兵・内戦 | EN: revolt, uprising, revolution, coup

## 外交・関係 / Diplomacy & Relations

- **Authorization** (許可・承認 / Authorization): JA: 許可・緩和・認定・公認・許す・承認・独立承認 | EN: permit, approve, authorize, recognize
- **Communication** (意見表明・言明 / Communication): JA: 主張・説得・提唱・提示・約束 | EN: assert, persuade, propose, promise
- **ConflictRupture** (対立・断交 / Conflict Rupture): JA: 対立・断交・破棄・離反・脱退・絶交・決裂・国交断絶 | EN: rupture, sever ties, withdraw
- **Declaration** (宣言・布告 / Declaration): JA: 宣言・独立宣言・宣戦布告・通告・布告・発効・声明・表明 | EN: declare, proclaim, announce
- **DemandOrder** (要求・命令 / Demand Order): JA: 要求・要請・命令・発令・通達・勧告・最後通牒・警告 | EN: demand, order, ultimatum
- **DiplomaticNegotiation** (外交交渉 / Diplomatic Negotiation): JA: 交渉・調停・仲介・会見・会談・訪問・遣使・謁見・協議 | EN: negotiate, mediate, confer
- **Rejection** (拒否・否定 / Rejection): JA: 拒否・否定・拒絶・否決・却下・批准拒否・調印拒否 | EN: refuse, reject, veto, deny
- **TreatyAgreement** (条約・合意 / Treaty Agreement): JA: 締結・調印・批准・同盟・和約・和平・承認・受諾・合意 | EN: conclude a treaty, ratify, alliance

## 政治・制度 / Political & Institutional

- **Abdication** (退位・失脚 / Abdication): JA: 退位・辞職・失脚・退陣・解任・廃位・総辞職・引退 | EN: abdicate, resign, be dismissed
- **Accession** (即位・就任 / Accession): JA: 即位・戴冠・就任・任命・冊封・選出・当選・再即位 | EN: accede, enthrone, appoint
- **Legislation** (制定・立法 / Legislation): JA: 制定・公布・発布・施行・改革・改正・採択・決議・可決 | EN: enact, promulgate, reform, adopt

## 存在・ライフサイクル / Existence & Lifecycle

- **Beginning** (誕生・始まり / Beginning): JA: 誕生・生まれる・開始・始まる・登場・起こる・勃発・発生 | EN: begin, arise, break out, emerge
- **Death** (死亡 / Death): JA: 死去・死亡・没・崩御・戦死・病死・敗死・薨去 | EN: die, pass away, die in battle
- **Dissolution** (滅亡・解体 / Dissolution): JA: 滅亡・崩壊・解体・解散・廃止・終結・消滅・壊滅・終了・中止・打ち切り・終わる | EN: fall, collapse, dissolve, terminate
- **Foundation** (建国・成立 / Foundation): JA: 成立・建国・樹立・創設・設立・結成・発足・建立・統一 | EN: found, establish, form
- **IndependenceSeparation** (独立・分離 / Independence Separation): JA: 独立・再独立・分離独立・分裂・自立・分立・自治 | EN: gain independence, secede, split

## 文化・経済・知識 / Culture, Economy & Knowledge

- **ConstructionProduction** (建設・生産 / Construction Production): JA: 建設・建造・建築・製造・鋳造・着工・完成・作成・開発・竣工 | EN: build, construct, manufacture
- **CulturalExpression** (文化・宗教・創作 / Cultural Expression): JA: 布教・伝来・伝道・改宗・列聖・刊行・著す・執筆・創作・初演・撮影・出版・放送 | EN: preach, publish, compose, perform
- **ExplorationDiscovery** (探検・発見 / Exploration Discovery): JA: 探検・発見・航海・世界周航・世界一周・調査・登頂・踏査・開拓 | EN: explore, discover, voyage, survey
- **ScientificInvention** (科学・技術・発明 / Scientific Invention): JA: 発明・発見・改良・発達・解明・実験・研究・開発・設計・打ち上げ | EN: invent, discover, experiment
- **TradeEconomy** (通商・経済 / Trade Economy): JA: 通商・貿易・販売・輸入・輸出・開港・課税・略奪・採掘・金融・開通・就航 | EN: trade, import, export, tax

## 汎用 / General

- **Failure** (失敗 / Failure): JA: 失敗・挫折・未遂・頓挫・失敗に終わる | EN: fail, be frustrated, abort
- **General** (一般・汎用 / General): JA: 参加・計画・実施・展開・活動・なる・する・流入・干渉・定着 | EN: participate, plan, carry out, become
- **PossessionTransfer** (授与・移譲 / Possession Transfer): JA: 授与・寄進・あたえる・付与・得る・朝貢・献上 | EN: grant, bestow, endow, pay tribute
- **Success** (成功 / Success): JA: 成功・達成・完遂・実現・果たす・成就 | EN: succeed, accomplish, achieve

## 状態・変遷 / State & Transition

- **DeEscalation** (縮小・減退 / De-escalation): JA: 衰退・縮小・弱体化・後退・鎮静化・減退 | EN: decline, shrink, weaken
- **Escalation** (拡大・激化 / Escalation): JA: 拡大・強化・激化・過激化・増大・躍進・勢力拡大・本格化 | EN: expand, intensify, escalate
- **Movement** (移動・遷都 / Movement): JA: 遷都・移転・移住・移民・行く・出発・到達・漂着・来航・亡命・帰国 | EN: relocate, migrate, arrive, flee
- **Release** (解放・返還 / Release): JA: 解放・釈放・返還・撤回・引き渡し・解除・撤廃・特赦 | EN: release, return, lift, pardon
- **Repetition** (反復・再 / Repetition): JA: 再襲来・再奪回・再認定・再軍備・再結成 | EN: recur, happen again, resume
- **Revival** (復興・回復 / Revival): JA: 再建・復活・復興・再興・回復・復帰・再生・再統一・名誉回復 | EN: revive, restore, rebuild
- **Suspension** (中断・停止 / Suspension): JA: 停止・中断・休戦・停戦・収束・沈静化・休業・停滞・更新せず | EN: suspend, halt, truce, stagnate
- **Transformation** (変容・転換 / Transformation): JA: 改宗・イスラーム化・民主化・近代化・国有化・西洋化・独裁化・公然化・表面化 | EN: convert, democratize, nationalize

