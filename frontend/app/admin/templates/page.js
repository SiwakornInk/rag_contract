'use client'
import { useEffect, useState } from 'react'
import { listTemplates, uploadTemplate } from '@/utils/api'

export default function AdminTemplatesPage(){
  const [file, setFile] = useState(null)
  const [docType, setDocType] = useState('')
  const [language, setLanguage] = useState('')
  const [uploading, setUploading] = useState(false)
  const [items, setItems] = useState([])

  useEffect(()=>{
    const load = async () => {
      const d = await listTemplates()
      setItems(d.templates||[])
    }
    load()
  },[])

  const doUpload = async () => {
    if(!file) return
    setUploading(true)
    try{
      await uploadTemplate(file, docType, language)
      const d = await listTemplates()
      setItems(d.templates||[])
      setFile(null)
    } finally { setUploading(false) }
  }

  return (
    <div style={{maxWidth:900, margin:'20px auto', background:'#fff', padding:20, borderRadius:8}}>
      <h1>🧩 จัดการแม่แบบ (Admin)</h1>
      <div style={{display:'flex', gap:10, alignItems:'center'}}>
  <input type="file" accept=".pdf,.docx" onChange={e=>setFile(e.target.files[0]||null)} />
        <input placeholder="ประเภทเอกสาร (เช่น สัญญาเช่า)" value={docType} onChange={e=>setDocType(e.target.value)} />
        <input placeholder="ภาษา (th/en)" value={language} onChange={e=>setLanguage(e.target.value)} />
        <button onClick={doUpload} disabled={uploading || !file} style={{padding:'8px 12px'}}>{uploading? 'กำลังอัปโหลด...' : 'อัปโหลด'}</button>
      </div>
      <h3 style={{marginTop:20}}>รายการแม่แบบ</h3>
      <ul>
        {items.map(i=> <li key={i.id}>{i.name} · {i.original_filename} · {i.doc_type} · {i.language} · {i.fields_count} ช่อง</li>)}
      </ul>
    </div>
  )
}
