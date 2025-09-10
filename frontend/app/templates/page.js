'use client'
import { useEffect, useState } from 'react'
import { listTemplates, getTemplateFields, generateContract } from '@/utils/api'

export default function TemplatesPage() {
  const [templates, setTemplates] = useState([])
  const [selected, setSelected] = useState(null)
  const [fields, setFields] = useState([])
  const [values, setValues] = useState({})
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const data = await listTemplates()
        setTemplates(data.templates || [])
      } finally { setLoading(false) }
    }
    load()
  }, [])

  const selectTemplate = async (t) => {
    setSelected(t)
    setFields([])
    setValues({})
    const data = await getTemplateFields(t.id)
    const fs = data.fields || []
    setFields(fs)
    const init = {}
    fs.forEach(f => { if (f.placeholder_name) init[f.placeholder_name] = '' })
    setValues(init)
  }

  const handleChange = (k, v) => setValues(prev => ({ ...prev, [k]: v }))

  const handleGenerate = async () => {
    if (!selected) return
    setGenerating(true)
    try {
      const blob = await generateContract(selected.id, values)
      const url = window.URL.createObjectURL(new Blob([blob]))
      const a = document.createElement('a')
      a.href = url
      a.download = `${selected.name}_filled.docx`
      a.click()
      window.URL.revokeObjectURL(url)
    } finally { setGenerating(false) }
  }

  if (loading) return <div style={{padding:20}}>กำลังโหลด...</div>

  return (
    <div style={{maxWidth:1000, margin:'20px auto', background:'#fff', padding:20, borderRadius:8}}>
      <h1>📑 แม่แบบสัญญา</h1>
      <div style={{display:'flex', gap:20}}>
        <div style={{flex:1}}>
          <h3>รายการแม่แบบ</h3>
          <div>
            {templates.map(t=> (
              <div key={t.id}
                   onClick={()=>selectTemplate(t)}
                   style={{padding:'10px 12px', border:'1px solid #e5e7eb', borderRadius:6, marginBottom:8, cursor:'pointer',
                           background: selected?.id===t.id?'#f1f5f9':'#fff'}}>
                <div style={{fontWeight:600}}>{t.name}</div>
                <div style={{fontSize:12, color:'#64748b'}}>
                  {t.original_filename} · {t.doc_type} · {t.language} · {t.fields_count} ช่อง
                </div>
              </div>
            ))}
            {templates.length===0 && <div>ยังไม่มีแม่แบบ</div>}
          </div>
        </div>
        <div style={{flex:2}}>
          <h3>กรอกข้อมูล</h3>
          {!selected && <div>เลือกแม่แบบทางซ้าย</div>}
          {selected && fields.length===0 && <div>ไม่มีช่องที่ต้องกรอก (เอกสารนี้อาจไม่ต้องกรอก)</div>}
          {selected && fields.length>0 && (
            <>
              <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12}}>
                {fields.map((f, idx)=> (
                  <div key={idx} style={{display:'flex', flexDirection:'column'}}>
                    <label style={{fontSize:13, color:'#111827', marginBottom:6}}>{f.label || f.placeholder_name}</label>
                    <input value={values[f.placeholder_name]||''}
                           onChange={e=>handleChange(f.placeholder_name, e.target.value)}
                           placeholder={f.context || ''}
                           style={{padding:'10px 12px', border:'1px solid #cbd5e1', borderRadius:6}} />
                  </div>
                ))}
              </div>
              <button onClick={handleGenerate} disabled={generating}
                      style={{marginTop:16, padding:'10px 14px', background:'#1e3a8a', color:'#fff', border:'none', borderRadius:6, cursor:'pointer'}}
                      onMouseEnter={(e)=> e.currentTarget.style.background='#1e40af'}
                      onMouseLeave={(e)=> e.currentTarget.style.background='#1e3a8a'}>
                {generating ? 'กำลังสร้าง...' : 'สร้างร่างสัญญา (.docx)'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
