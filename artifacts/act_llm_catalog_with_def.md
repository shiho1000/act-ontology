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
  (意図的かつ非正当な殺害。)
  (The intentional and illegitimate killing of one or more persons.)
- **CaptureAndPunishment** (拘束・処罰 / Capture And Punishment): JA: 逮捕・捕縛・拉致・配流・処刑・斬首・刑死・捕囚・監禁 | EN: arrest, imprison, execute, exile
  (人物の拘束・勾留・司法的処罰。)
  (The capture, detention, or judicial punishment of a person.)
- **ConquestOccupation** (征服・占領 / Conquest Occupation): JA: 征服・占領・占拠・制圧・支配・領有・支配下におく・駐留 | EN: conquer, occupy, annex
  (ある領域・政体に対する支配の確立（征服する側の視点）。)
  (The active establishment of control over a territory or polity, from the conqueror's perspective.)
- **Defeat** (敗北・降伏 / Defeat): JA: 敗北・大敗・惨敗・降伏・投降・撤退・敗走 | EN: defeat, surrender, retreat
  (個別の出来事としての軍事的敗北（敗れる側の視点）。)
  (A military defeat as a discrete event, from the losing side's perspective.)
- **DisputeConflict** (紛争・衝突 / Dispute Conflict): JA: 衝突・抗争・参戦・内戦・交戦・武力衝突・戦闘・戦争 | EN: clash, war, civil war, combat
  (勢力間の武力衝突または交戦状態。)
  (An armed clash or state of hostilities between parties.)
- **MilitaryAttack** (軍事攻撃 / Military Attack): JA: 攻撃・侵攻・侵入・包囲・攻略・撃退・進軍・出兵・上陸・進出 | EN: attack, invade, besiege, advance
  (ある勢力が他勢力に対して仕掛ける軍事的な攻勢行為。)
  (An armed offensive action launched by one party against another.)
- **Subjugation** (服属・臣従 / Subjugation): JA: 服属・臣従する・支配下に入る・服従・帰順 | EN: submit, become a vassal
  (服属・従属関係の確立（服属する側の視点）。)
  (Establishment of a subordination/vassalage relationship, described from the subordinated side's perspective.)
- **Suppression** (弾圧・抑圧 / Suppression): JA: 弾圧・鎮圧・迫害・排除・禁止・布教禁止・非合法化 | EN: suppress, persecute, ban
  (権力側による弾圧・禁止行為（抑圧する側の視点）。)
  (Coercive action by an authority to suppress or prohibit, from the suppressing side.)
- **Victory** (勝利 / Victory): JA: 勝利・大勝・平定・撃破・完勝・戦勝 | EN: victory, triumph, rout
  (軍事的交戦における勝利という結果。)
  (A successful outcome of a military engagement.)

## 集団抵抗・反乱 / Collective Resistance & Revolt

- **ResistanceProtest** (抵抗・抗議 / Resistance Protest): JA: 抵抗・抗議・反対・ボイコット・デモ・批判・請願・独立運動 | EN: resist, protest, boycott, petition
  (抗議・抵抗による組織的・継続的な反対の表明。)
  (Organized or sustained opposition expressed through protest or resistance.)
- **RevoltInsurrection** (反乱・革命 / Revolt Insurrection): JA: 反乱・蜂起・一揆・暴動・革命・クーデター・挙兵・内戦 | EN: revolt, uprising, revolution, coup
  (既存権力に対する武装蜂起・革命的行動。)
  (An armed uprising or revolutionary action against an established authority.)

## 外交・関係 / Diplomacy & Relations

- **Authorization** (許可・承認 / Authorization): JA: 許可・緩和・認定・公認・許す・承認・独立承認 | EN: permit, approve, authorize, recognize
  (公式な許可・承認の付与。)
  (An official granting of permission or approval.)
- **Communication** (意見表明・言明 / Communication): JA: 主張・説得・提唱・提示・約束 | EN: assert, persuade, propose, promise
  (強制力を伴わない非公式な発話行為（主張・説得・提唱・約束など）。)
  (Non-coercive, non-official speech acts: asserting, persuading, proposing, promising.)
- **ConflictRupture** (対立・断交 / Conflict Rupture): JA: 対立・断交・破棄・離反・脱退・絶交・決裂・国交断絶 | EN: rupture, sever ties, withdraw
  (関係・同盟・合意の断絶・決裂。)
  (The rupture or breakdown of a relationship, alliance, or agreement.)
- **Declaration** (宣言・布告 / Declaration): JA: 宣言・独立宣言・宣戦布告・通告・布告・発効・声明・表明 | EN: declare, proclaim, announce
  (公式・対外的な宣言・布告。)
  (An official or outward public declaration.)
- **DemandOrder** (要求・命令 / Demand Order): JA: 要求・要請・命令・発令・通達・勧告・最後通牒・警告 | EN: demand, order, ultimatum
  (強制力を伴う発話行為（要求・命令）。)
  (A speech act carrying compulsory force, such as a demand or order.)
- **DiplomaticNegotiation** (外交交渉 / Diplomatic Negotiation): JA: 交渉・調停・仲介・会見・会談・訪問・遣使・謁見・協議 | EN: negotiate, mediate, confer
  (勢力間の外交的接触・交渉。)
  (Diplomatic contact or negotiation between parties.)
- **Rejection** (拒否・否定 / Rejection): JA: 拒否・否定・拒絶・否決・却下・批准拒否・調印拒否 | EN: refuse, reject, veto, deny
  (提案・要求・主張・条約等に対する不同意の意思表示。)
  (An expression of non-consent toward a proposal, demand, assertion, or treaty: refusal, negation, rejection, veto.)
- **TreatyAgreement** (条約・合意 / Treaty Agreement): JA: 締結・調印・批准・同盟・和約・和平・承認・受諾・合意 | EN: conclude a treaty, ratify, alliance
  (条約・公式合意の締結・批准。)
  (The conclusion or ratification of a treaty or formal agreement.)

## 政治・制度 / Political & Institutional

- **Abdication** (退位・失脚 / Abdication): JA: 退位・辞職・失脚・退陣・解任・廃位・総辞職・引退 | EN: abdicate, resign, be dismissed
  (王位・官職・公的地位からの離脱。)
  (Leaving a throne, office, or official position.)
- **Accession** (即位・就任 / Accession): JA: 即位・戴冠・就任・任命・冊封・選出・当選・再即位 | EN: accede, enthrone, appoint
  (王位・官職・公的地位への就任。)
  (Assuming a throne, office, or official position.)
- **Legislation** (制定・立法 / Legislation): JA: 制定・公布・発布・施行・改革・改正・採択・決議・可決 | EN: enact, promulgate, reform, adopt
  (法・制度の制定・公布・改革。)
  (The enactment, promulgation, or reform of laws and institutional rules.)

## 存在・ライフサイクル / Existence & Lifecycle

- **Beginning** (誕生・始まり / Beginning): JA: 誕生・生まれる・開始・始まる・登場・起こる・勃発・発生 | EN: begin, arise, break out, emerge
  (出来事・現象・存在の発生・開始。)
  (The coming into being or onset of an event, phenomenon, or entity.)
- **Death** (死亡 / Death): JA: 死去・死亡・没・崩御・戦死・病死・敗死・薨去 | EN: die, pass away, die in battle
  (人物の自然死または戦死。)
  (The natural or battlefield death of a person.)
- **Dissolution** (滅亡・解体 / Dissolution): JA: 滅亡・崩壊・解体・解散・廃止・終結・消滅・壊滅・終了・中止・打ち切り・終わる | EN: fall, collapse, dissolve, terminate
  (主体の消滅、または出来事・プロセスの確定的終了。)
  (The disappearance of a subject or the definitive termination of an event or process.)
- **Foundation** (建国・成立 / Foundation): JA: 成立・建国・樹立・創設・設立・結成・発足・建立・統一 | EN: found, establish, form
  (国家・組織・体制の建国・設立。)
  (The founding or formal establishment of a state, organization, or system.)
- **IndependenceSeparation** (独立・分離 / Independence Separation): JA: 独立・再独立・分離独立・分裂・自立・分立・自治 | EN: gain independence, secede, split
  (政体の独立獲得・分離。)
  (The gaining of independence or separation of a polity from another.)

## 文化・経済・知識 / Culture, Economy & Knowledge

- **ConstructionProduction** (建設・生産 / Construction Production): JA: 建設・建造・建築・製造・鋳造・着工・完成・作成・開発・竣工 | EN: build, construct, manufacture
  (物理的な構造物・物品の建設・製造・生産。)
  (The construction, manufacture, or production of physical works or goods.)
- **CulturalExpression** (文化・宗教・創作 / Cultural Expression): JA: 布教・伝来・伝道・改宗・列聖・刊行・著す・執筆・創作・初演・撮影・出版・放送 | EN: preach, publish, compose, perform
  (文化的・創作的・宗教的な表現および実践。)
  (Cultural, creative, or religious expression and practice.)
- **ExplorationDiscovery** (探検・発見 / Exploration Discovery): JA: 探検・発見・航海・世界周航・世界一周・調査・登頂・踏査・開拓 | EN: explore, discover, voyage, survey
  (探検・発見の行為。)
  (An act of exploration or discovery.)
- **ScientificInvention** (科学・技術・発明 / Scientific Invention): JA: 発明・発見・改良・発達・解明・実験・研究・開発・設計・打ち上げ | EN: invent, discover, experiment
  (科学的・技術的な発明・発見・研究。)
  (Scientific or technological invention, discovery, or research.)
- **TradeEconomy** (通商・経済 / Trade Economy): JA: 通商・貿易・販売・輸入・輸出・開港・課税・略奪・採掘・金融・開通・就航 | EN: trade, import, export, tax
  (商業・貿易・経済活動。)
  (Commercial, trade, or economic activity.)

## 汎用 / General

- **Failure** (失敗 / Failure): JA: 失敗・挫折・未遂・頓挫・失敗に終わる | EN: fail, be frustrated, abort
  (目的・企ての失敗・挫折。)
  (The failure or frustration of an aim or undertaking.)
- **General** (一般・汎用 / General): JA: 参加・計画・実施・展開・活動・なる・する・流入・干渉・定着 | EN: participate, plan, carry out, become
  (ドメイン中立、または単独では特定ActionTypeに確定しない意味的に未指定の動作。)
  (Domain-neutral or semantically underspecified actions that do not resolve to a specific ActionType on their own.)
- **PossessionTransfer** (授与・移譲 / Possession Transfer): JA: 授与・寄進・あたえる・付与・得る・朝貢・献上 | EN: grant, bestow, endow, pay tribute
  (経済的枠組みを伴わない、物品・称号・権利の一方から他方への移転。)
  (Transfer of possession of an object, title, or right from one party to another, without an inherent commercial frame.)
- **Success** (成功 / Success): JA: 成功・達成・完遂・実現・果たす・成就 | EN: succeed, accomplish, achieve
  (目的・企ての達成・成功。)
  (The successful accomplishment of an aim or undertaking.)

## 状態・変遷 / State & Transition

- **DeEscalation** (縮小・減退 / De-escalation): JA: 衰退・縮小・弱体化・後退・鎮静化・減退 | EN: decline, shrink, weaken
  (規模・強度・程度の縮小・減衰（存在はするが弱まる）。)
  (Decrease or gradual decline in scale, intensity, or degree (still existing, but weakening).)
- **Escalation** (拡大・激化 / Escalation): JA: 拡大・強化・激化・過激化・増大・躍進・勢力拡大・本格化 | EN: expand, intensify, escalate
  (規模・強度・程度の増大。)
  (Increase in scale, intensity, or degree.)
- **Movement** (移動・遷都 / Movement): JA: 遷都・移転・移住・移民・行く・出発・到達・漂着・来航・亡命・帰国 | EN: relocate, migrate, arrive, flee
  (人・集団・首都の物理的移動。)
  (Physical relocation of persons, groups, or a capital.)
- **Release** (解放・返還 / Release): JA: 解放・釈放・返還・撤回・引き渡し・解除・撤廃・特赦 | EN: release, return, lift, pardon
  (人物・領域・制限の解放・返還・解除。)
  (The release, return, or lifting of a person, territory, or restriction.)
- **Repetition** (反復・再 / Repetition): JA: 再襲来・再奪回・再認定・再軍備・再結成 | EN: recur, happen again, resume
  (以前に起きた動作・出来事が再び起こること。接頭辞「再」が示すアスペクト標識。)
  (The recurrence of an action or event that has happened before; an aspectual marker signalled by the 再 prefix.)
- **Revival** (復興・回復 / Revival): JA: 再建・復活・復興・再興・回復・復帰・再生・再統一・名誉回復 | EN: revive, restore, rebuild
  (かつて存在した実体・状態の復興・回復。)
  (The restoration or revival of a previously existing entity or state.)
- **Suspension** (中断・停止 / Suspension): JA: 停止・中断・休戦・停戦・収束・沈静化・休業・停滞・更新せず | EN: suspend, halt, truce, stagnate
  (活動・プロセスの一時的・再開可能な停止。)
  (Temporary, resumable cessation of an activity or process.)
- **Transformation** (変容・転換 / Transformation): JA: 改宗・イスラーム化・民主化・近代化・国有化・西洋化・独裁化・公然化・表面化 | EN: convert, democratize, nationalize
  (状態・性質の変化（多くは「〜化」で表現）。)
  (A change of state or nature, typically expressed by the '-ka' suffix.)

