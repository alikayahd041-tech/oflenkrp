import { FormEvent, useEffect, useMemo, useState } from "react";
import { supabase } from "../lib/supabase";

type ServerKey = "tr" | "ksa";
type Profile = { id: string; display_name: string | null; role: string; server: ServerKey };
type Complaint = {
  id: string; server: ServerKey; category: string; accused_name: string; author_name: string;
  static_id: string; complaint_date: string; complaint_time: string; details: string;
  evidence_url: string | null; status: string; created_at: string;
};
type Application = { id: string; server: ServerKey; type: string; applicant_name: string; status: string; created_at: string; answers: Record<string,string> };

const roles = [
  "Project Manager", "Deputy Project Manager", "Project Coordinator",
  "Chief Administrator", "Deputy Chief Administrator", "Senior Administrator",
  "Junior Administrator", "Server Administrator", "Admin Assistant"
];
const roleLabels: Record<string,string> = {
  "Project Manager": "Project Manager",
  "Deputy Project Manager": "Deputy Project Manager",
  "Project Coordinator": "Project Coordinator",
  "Chief Administrator": "Chief Administrator",
  "Deputy Chief Administrator": "Deputy Chief Administrator",
  "Senior Administrator": "Senior Administrator",
  "Junior Administrator": "Junior Administrator",
  "Server Administrator": "Server Administrator",
  "Admin Assistant": "Admin Assistant",
  member: "Member"
};
const trRules = ["Genel Kurallar", "Devlet Kuralları", "Liderlik Kuralları", "Yeşil Bölge Kuralları"];
const ksaRules = ["القوانين العامة", "قوانين الحكومة", "قوانين القيادة", "قوانين المنطقة الآمنة"];
const government = ["Hastane", "Ordu", "Şehir Polisi", "FBI", "Medya", "Belediye"];
const getto = ["Fangs", "Wolves", "Rawens"];

function AppButton({children, ...props}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className="btn" {...props}>{children}</button>;
}

export default function Home() {
  const [server, setServer] = useState<ServerKey>("tr");
  const [lang, setLang] = useState<"tr"|"ar">("tr");
  const [user, setUser] = useState<any>(null);
  const [profile, setProfile] = useState<Profile|null>(null);
  const [tab, setTab] = useState("home");
  const [message, setMessage] = useState("");
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [rules, setRules] = useState<any[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [complaintType, setComplaintType] = useState("player");
  const [appType, setAppType] = useState("leadership");
  const [form, setForm] = useState<Record<string,string>>({});
  const isAr = server === "ksa" || lang === "ar";
  const isAdmin = !!profile && profile.role !== "member";
  const isProjectManager = profile?.role === "Project Manager";
  const canReview = isAdmin;
  const labels = useMemo(() => isAr ? {
    choose:"اختر الخادم", tr:"الخادم التركي", ksa:"الخادم السعودي", home:"الرئيسية", rules:"القوانين",
    complaints:"الشكاوى", applications:"التقديمات", admin:"لوحة الإدارة", login:"تسجيل الدخول",
    logout:"تسجيل الخروج", email:"البريد الإلكتروني", password:"كلمة المرور", signIn:"دخول",
    register:"إنشاء حساب", title:"منتدى OFF Leank RP", intro:"مجتمع رول بلاي رسمي",
    newComplaint:"إرسال شكوى", newApplication:"إرسال طلب", submit:"إرسال", status:"الحالة",
    accused:"اسم الشخص المشتكى عليه", author:"اسمك داخل اللعبة", staticId:"الرقم الثابت",
    date:"التاريخ", time:"الوقت", details:"تفاصيل الشكوى", evidence:"رابط الدليل",
    player:"شكوى لاعب", adminComplaint:"شكوى ضد إداري", leadership:"طلب قيادة",
    administrator:"طلب إداري", assistant:"طلب مساعد إداري", pending:"قيد المراجعة",
    accepted:"مقبول", rejected:"مرفوض", review:"مراجعة", accept:"قبول", reject:"رفض",
    noItems:"لا توجد سجلات بعد.", role:"رتبتك", serverLabel:"الخادم"
  } : {
    choose:"Sunucu seç", tr:"Türkiye Sunucusu", ksa:"KSA Sunucusu", home:"Ana Sayfa", rules:"Kurallar",
    complaints:"Şikâyetler", applications:"Başvurular", admin:"Yönetim Paneli", login:"Giriş",
    logout:"Çıkış yap", email:"E-posta", password:"Şifre", signIn:"Giriş yap",
    register:"Hesap oluştur", title:"OFF Leank RP Forum", intro:"Resmî RolePlay topluluğu",
    newComplaint:"Şikâyet gönder", newApplication:"Başvuru gönder", submit:"Gönder", status:"Durum",
    accused:"Şikâyet edilen kişinin adı", author:"Oyun içi adın", staticId:"Static ID",
    date:"Tarih", time:"Saat", details:"Şikâyet ayrıntıları", evidence:"Kanıt bağlantısı",
    player:"Oyuncu şikâyeti", adminComplaint:"Yönetici şikâyeti", leadership:"Liderlik başvurusu",
    administrator:"Yönetici başvurusu", assistant:"Asistan başvurusu", pending:"İnceleniyor",
    accepted:"Kabul edildi", rejected:"Reddedildi", review:"İncele", accept:"Kabul et", reject:"Reddet",
    noItems:"Henüz kayıt yok.", role:"Rolün", serverLabel:"Sunucu"
  }, [isAr]);

  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({data}) => setUser(data.session?.user ?? null));
    const {data:{subscription}} = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!supabase || !user) { setProfile(null); return; }
    let alive = true;
    supabase.from("profiles").select("id,display_name,role,server").eq("id", user.id).maybeSingle()
      .then(({data}) => { if (alive && data) setProfile(data as Profile); });
    return () => { alive = false; };
  }, [user]);

  async function loadData() {
    if (!supabase) return;
    const [{data:c},{data:a},{data:r}] = await Promise.all([
      supabase.from("complaints").select("*").eq("server",server).order("created_at",{ascending:false}).limit(100),
      supabase.from("applications").select("*").eq("server",server).order("created_at",{ascending:false}).limit(100),
      supabase.from("rules").select("*").eq("server",server).order("sort_order")
    ]);
    setComplaints((c ?? []) as Complaint[]);
    setApplications((a ?? []) as Application[]);
    setRules(r ?? []);
  }
  useEffect(() => { void loadData(); }, [server, user]);

  async function auth(e: FormEvent, mode:"login"|"register") {
    e.preventDefault();
    if (!supabase) { setMessage("Önce .env.local dosyasına Supabase URL ve anon key ekle."); return; }
    setBusy(true); setMessage("");
    const result = mode === "login"
      ? await supabase.auth.signInWithPassword({email,password})
      : await supabase.auth.signUp({email,password});
    setBusy(false);
    setMessage(result.error?.message ?? (mode === "register" ? "Hesap oluşturuldu. E-posta doğrulaması gerekiyorsa gelen kutunu kontrol et." : "Giriş başarılı."));
  }

  async function submitComplaint(e: FormEvent) {
    e.preventDefault();
    if (!supabase || !user) { setMessage("Şikâyet göndermek için giriş yapmalısın."); return; }
    const {error} = await supabase.from("complaints").insert({
      server, category:complaintType, accused_name:form.accused || "", author_name:form.author || "",
      static_id:form.static_id || "", complaint_date:form.date || "", complaint_time:form.time || "",
      details:form.details || "", evidence_url:form.evidence || null
    });
    setMessage(error?.message ?? "Şikâyet gönderildi."); setForm({});
    if (!error) { setTab("complaints"); void loadData(); }
  }

  const appQuestions: Record<string,string[]> = {
    leadership: ["Gerçek adınız","Yaşınız","Saat diliminiz","Günlük ortalama aktiflik süreniz","Discord kullanıcı adınız","Oyun içi isminiz","Kalıcı oyuncu ID’niz","Liderlik başvurusu yapılan organizasyon","Neden özellikle bu organizasyonun lideri olmak istiyorsunuz? (3 detaylı açıklama)","RolePlay’i geliştirmek için önerileriniz"],
    administrator: ["Gerçek adınız","Yaşınız","Saat diliminiz","Sunucu saatine göre aktif olduğunuz saatler","Günlük ortalama aktiflik süreniz","Discord kullanıcı adınız","Oyun içi isminiz","Kalıcı oyuncu ID’niz","Küratör olmak istediğiniz bölüm (Suç/Devlet)","Neden yönetici olmak istiyorsunuz?","Güçlü yönleriniz","En büyük zayıf yönleriniz","RP’den çıkıp sadece yönetici olmaya hazır mısınız?","Aktifliğinizi engelleyen bir durum var mı?"],
    assistant: ["Gerçek adınız","Yaşınız","Saat diliminiz","Sunucu saatine göre aktif olduğunuz saatler","Günlük ortalama aktiflik süreniz","Discord kullanıcı adınız","Oyun içi isminiz","Kalıcı oyuncu ID’niz","Neden asistan olmak istiyorsunuz?","Güçlü yönleriniz","En büyük zayıf yönleriniz","Aktifliğinizi engelleyen bir durum var mı?"]
  };

  async function submitApplication(e: FormEvent) {
    e.preventDefault();
    if (!supabase || !user) { setMessage("Başvuru göndermek için giriş yapmalısın."); return; }
    const {error} = await supabase.from("applications").insert({server,type:appType,applicant_name:form["Oyun içi isminiz"] || form["Gerçek adınız"] || "",answers:form});
    setMessage(error?.message ?? "Başvurun gönderildi."); setForm({});
    if (!error) { setTab("applications"); void loadData(); }
  }

  async function setStatus(table:"complaints"|"applications", id:string, status:string) {
    if (!supabase) return;
    const {error} = await supabase.from(table).update({status}).eq("id",id);
    setMessage(error?.message ?? "Durum güncellendi."); void loadData();
  }

  async function changeRole(targetId:string, role:string) {
    if (!supabase) return;
    const {error} = await supabase.rpc("set_member_role", {target_user_id:targetId, new_role:role});
    setMessage(error?.message ?? "Rol güncellendi.");
  }

  const title = isAr ? "OFF Leank RP" : "OFF Leank RP";
  const currentRules = server === "tr" ? trRules : ksaRules;

  return <main dir={isAr ? "rtl" : "ltr"} className={isAr ? "rtl" : ""}>
    <header className="topbar">
      <div className="brand"><span className="logo">OL</span><div><strong>OFF LEANK RP</strong><small>{labels.intro}</small></div></div>
      <div className="top-actions">
        <select aria-label={labels.choose} value={server} onChange={e => {setServer(e.target.value as ServerKey); setLang(e.target.value === "ksa" ? "ar" : "tr"); setTab("home");}}>
          <option value="tr">🇹🇷 TR — Türkçe</option><option value="ksa">🇸🇦 KSA — العربية</option>
        </select>
        {user ? <><span className="userchip">{profile?.role ?? "Member"}</span><AppButton onClick={() => supabase?.auth.signOut()}>{labels.logout}</AppButton></> : <a className="btn" href="#auth">{labels.login}</a>}
      </div>
    </header>

    <section className="hero">
      <div className="hero-copy"><span className="eyebrow">{server === "tr" ? "🇹🇷 TÜRKİYE SUNUCUSU" : "🇸🇦 خادم المملكة العربية السعودية"}</span>
        <h1>{title}</h1><p>{labels.intro}. {server === "tr" ? "Kurallar, topluluk başvuruları ve şikâyetler tek yerde." : "القوانين والتقديمات والشكاوى في مكان واحد."}</p>
        <div className="hero-actions"><AppButton onClick={() => setTab("rules")}>{labels.rules}</AppButton><AppButton onClick={() => setTab("applications")}><span>{labels.applications}</span></AppButton></div>
      </div>
      <div className="hero-mark"><span>{server === "tr" ? "🇹🇷" : "🇸🇦"}</span><strong>{server === "tr" ? "TR COMMUNITY" : "KSA COMMUNITY"}</strong><small>ROLEPLAY • COMMUNITY • FAIR PLAY</small></div>
    </section>

    <nav className="nav">
      {[[ "home",labels.home],["rules",labels.rules],["complaints",labels.complaints],["applications",labels.applications],...(isAdmin?[["admin",labels.admin]]:[])].map(([key,label]) =>
        <button key={key} className={tab===key?"navitem active":"navitem"} onClick={() => setTab(key as string)}>{label}</button>)}
    </nav>

    {!supabase && <div className="notice">Kurulum gerekli: Supabase projesi oluşturup .env.local dosyasını doldur.</div>}
    {message && <div className="notice" role="status">{message}<button onClick={() => setMessage("")}>×</button></div>}

    {tab === "home" && <section className="content">
      <div className="section-heading"><div><span className="eyebrow">COMMUNITY CENTER</span><h2>{server==="tr"?"Sunucu Merkezi":"مركز الخادم"}</h2></div><p>{server==="tr"?"İhtiyacın olan bölüme geç.":"انتقل إلى القسم الذي تحتاجه."}</p></div>
      <div className="cards">
        <article className="tile"><span className="tile-icon">§</span><h3>{labels.rules}</h3><p>{server==="tr"?"Sunucu kurallarını oku.":"اقرأ قوانين الخادم."}</p><AppButton onClick={() => setTab("rules")}>Aç →</AppButton></article>
        <article className="tile"><span className="tile-icon">!</span><h3>{labels.complaints}</h3><p>{server==="tr"?"Oyuncu veya yönetici hakkında bildirim oluştur.":"قدّم شكوى عن لاعب أو إداري."}</p><AppButton onClick={() => setTab("complaints")}>Aç →</AppButton></article>
        <article className="tile"><span className="tile-icon">✦</span><h3>{labels.applications}</h3><p>{server==="tr"?"Liderlik ve ekip başvurusu gönder.":"قدّم طلب قيادة أو إدارة."}</p><AppButton onClick={() => setTab("applications")}>Aç →</AppButton></article>
      </div>
      <div className="section-heading compact"><div><span className="eyebrow">ORGANIZATIONS</span><h2>{server==="tr"?"Devlet Kurumları":"المؤسسات الحكومية"}</h2></div></div>
      <div className="pills">{(server==="tr"?government:["المستشفى","الجيش","شرطة المدينة","FBI","الإعلام","البلدية"]).map(x=><span className="pill" key={x}>{x} <small>• Lider</small></span>)}</div>
      <div className="section-heading compact"><div><span className="eyebrow">GETTO</span><h2>{server==="tr"?"Getto Organizasyonları":"منظمات الغيتو"}</h2></div></div>
      <div className="pills">{getto.map(x=><span className="pill" key={x}>{x} <small>• Lider</small></span>)}</div>
    </section>}

    {tab === "rules" && <section className="content"><div className="section-heading"><div><span className="eyebrow">SERVER POLICIES</span><h2>{labels.rules}</h2></div><p>{server==="tr"?"Kuralları yetkililer düzenleyebilir.":"يمكن للإدارة تعديل القوانين."}</p></div>
      <div className="rule-list">{currentRules.map((name,i) => {
        const saved = rules.find(r=>r.title===name);
        return <article className="rule" key={name}><div className="rule-number">0{i+1}</div><div><h3>{name}</h3><p>{saved?.body || (server==="tr"?"Bu bölümün içeriği henüz eklenmedi. Yetkili ekip SQL üzerinden kural ekleyebilir.":"لم تتم إضافة محتوى هذا القسم بعد. يمكن للإدارة إضافة القوانين من قاعدة البيانات.")}</p></div></article>;
      })}</div>
      <h3>{server==="tr"?"Şirketler":"الشركات"}</h3><p className="muted">{server==="tr"?"Şirket içerikleri ve organizasyon açıklamaları bu alanda yayınlanabilir.":"يمكن نشر تفاصيل الشركات والمنظمات هنا."}</p>
    </section>}

    {tab === "complaints" && <section className="content"><div className="section-heading"><div><span className="eyebrow">REPORT CENTER</span><h2>{labels.complaints}</h2></div><span className="counter">{complaints.length} kayıt</span></div>
      {user ? <form className="panel formgrid" onSubmit={submitComplaint}>
        <h3 className="full">{labels.newComplaint}</h3>
        <label>{isAr?"نوع الشكوى":"Şikâyet türü"}<select value={complaintType} onChange={e=>setComplaintType(e.target.value)}><option value="player">{labels.player}</option><option value="admin">{labels.adminComplaint}</option></select></label>
        <label>{labels.accused}<input required value={form.accused||""} onChange={e=>setForm({...form,accused:e.target.value})}/></label>
        <label>{labels.author}<input required value={form.author||""} onChange={e=>setForm({...form,author:e.target.value})}/></label>
        <label>{labels.staticId}<input required value={form.static_id||""} onChange={e=>setForm({...form,static_id:e.target.value})}/></label>
        {complaintType==="admin" && <label>{isAr?"اسم الإداري":"Şikâyet edilen admin"}<input required value={form.admin_name||""} onChange={e=>setForm({...form,accused:e.target.value,admin_name:e.target.value})}/></label>}
        <label>{labels.date}<input type="date" required value={form.date||""} onChange={e=>setForm({...form,date:e.target.value})}/></label>
        <label>{labels.time}<input type="time" required value={form.time||""} onChange={e=>setForm({...form,time:e.target.value})}/></label>
        <label className="full">{labels.details}<textarea required rows={4} value={form.details||""} onChange={e=>setForm({...form,details:e.target.value})}/></label>
        <label className="full">{labels.evidence}<input type="url" placeholder="https://..." value={form.evidence||""} onChange={e=>setForm({...form,evidence:e.target.value})}/></label>
        <div className="full"><AppButton type="submit">{labels.submit}</AppButton></div>
      </form> : <div className="panel"><p>{server==="tr"?"Şikâyet göndermek için giriş yap.":"سجّل الدخول لإرسال شكوى."} <a href="#auth">{labels.login}</a></p></div>}
      <div className="stack">{complaints.map(c=><article className="record" key={c.id}><div className="record-top"><span className="tag">{c.category==="admin"?labels.adminComplaint:labels.player}</span><span className={"status "+c.status}>{c.status==="accepted"?labels.accepted:c.status==="rejected"?labels.rejected:labels.pending}</span></div><h3>{c.accused_name}</h3><p>{c.details}</p><small>{c.author_name} · ID {c.static_id} · {c.complaint_date} {c.complaint_time}</small>{c.evidence_url&&<p><a href={c.evidence_url} target="_blank" rel="noreferrer">Kanıtı aç</a></p>}
        {canReview&&<div className="record-actions"><AppButton onClick={()=>setStatus("complaints",c.id,"accepted")}>{labels.accept}</AppButton><AppButton onClick={()=>setStatus("complaints",c.id,"rejected")}>{labels.reject}</AppButton></div>}</article>)}</div>
      {!complaints.length&&<p className="muted">{labels.noItems}</p>}
    </section>}

    {tab === "applications" && <section className="content"><div className="section-heading"><div><span className="eyebrow">JOIN THE TEAM</span><h2>{labels.applications}</h2></div></div>
      {user ? <form className="panel formgrid" onSubmit={submitApplication}><h3 className="full">{labels.newApplication}</h3>
        <label className="full">{isAr?"نوع الطلب":"Başvuru türü"}<select value={appType} onChange={e=>{setAppType(e.target.value);setForm({});}}><option value="leadership">{labels.leadership}</option><option value="administrator">{labels.administrator}</option><option value="assistant">{labels.assistant}</option></select></label>
        {appQuestions[appType].map((q,i)=><label key={q} className={q.length>45?"full":""}>{i+1}. {q}<textarea required rows={q.length>45?3:1} value={form[q]||""} onChange={e=>setForm({...form,[q]:e.target.value})}/></label>)}
        <div className="full"><AppButton type="submit">{labels.submit}</AppButton></div>
      </form> : <div className="panel"><p>{server==="tr"?"Başvuru göndermek için giriş yap.":"سجّل الدخول لإرسال طلب."} <a href="#auth">{labels.login}</a></p></div>}
      <div className="stack">{applications.map(a=><article className="record" key={a.id}><div className="record-top"><span className="tag">{a.type}</span><span className={"status "+a.status}>{a.status==="accepted"?labels.accepted:a.status==="rejected"?labels.rejected:labels.pending}</span></div><h3>{a.applicant_name}</h3><small>{new Date(a.created_at).toLocaleString()}</small>{canReview&&<div className="record-actions"><AppButton onClick={()=>setStatus("applications",a.id,"accepted")}>{labels.accept}</AppButton><AppButton onClick={()=>setStatus("applications",a.id,"rejected")}>{labels.reject}</AppButton></div>}</article>)}</div>
      {!applications.length&&<p className="muted">{labels.noItems}</p>}
    </section>}

    {tab === "admin" && isAdmin && <section className="content"><div className="section-heading"><div><span className="eyebrow">STAFF ONLY</span><h2>{labels.admin}</h2></div></div>
      <div className="panel"><h3>{labels.role}</h3><p>{profile?.role}</p><p className="muted">Rol atama işlemi yalnızca Project Manager tarafından yapılabilir. Kullanıcı ID's
