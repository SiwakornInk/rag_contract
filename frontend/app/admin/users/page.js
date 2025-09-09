"use client"
import { useEffect, useState } from 'react'
import api from '@/utils/api'

const styles = {container:{maxWidth:'900px',margin:'40px auto',padding:'20px',background:'#fff',borderRadius:'12px',boxShadow:'0 4px 12px rgba(0,0,0,0.06)',fontFamily:'Prompt, sans-serif'},
title:{fontSize:'26px',fontWeight:'600',color:'#1e3a8a',marginBottom:'20px'},
section:{marginBottom:'30px'},
label:{display:'block',fontSize:'13px',color:'#475569',marginBottom:'4px'},
input:{width:'100%',padding:'10px 12px',border:'1px solid #cbd5e1',borderRadius:'6px',marginBottom:'12px',fontSize:'14px'},
select:{width:'100%',padding:'10px 12px',border:'1px solid #cbd5e1',borderRadius:'6px',marginBottom:'12px',fontSize:'14px'},
button:{padding:'10px 20px',background:'#1e3a8a',color:'#fff',border:'none',borderRadius:'6px',cursor:'pointer',fontSize:'14px',fontWeight:'500'},
table:{width:'100%',borderCollapse:'collapse'},
th:{textAlign:'left',padding:'10px',borderBottom:'2px solid #e2e8f0',fontSize:'12px',color:'#475569'},
td:{padding:'10px',borderBottom:'1px solid #f1f5f9',fontSize:'13px'},
badge:{display:'inline-block',padding:'2px 8px',borderRadius:'12px',background:'#eef2ff',color:'#3730a3',fontSize:'11px',fontWeight:500},
error:{background:'#fee2e2',color:'#991b1b',padding:'10px',borderRadius:'8px',fontSize:'13px',marginBottom:'15px'},
success:{background:'#ecfdf5',color:'#065f46',padding:'10px',borderRadius:'8px',fontSize:'13px',marginBottom:'15px'} }

export default function AdminUsersPage(){
  const [users,setUsers]=useState([])
  const [loading,setLoading]=useState(true)
  const [username,setUsername]=useState('')
  const [password,setPassword]=useState('')
  const [role,setRole]=useState('USER')
  const [level,setLevel]=useState('PUBLIC')
  const [error,setError]=useState('')
  const [success,setSuccess]=useState('')

  useEffect(()=>{
    if(typeof window!=='undefined'){
      if(localStorage.getItem('role')!=='ADMIN'){
        window.location.href='/'
        return
      }
    }
    load()
  },[])

  const load=async()=>{
    try{setLoading(true);const res=await api.get('/admin/users');setUsers(res.data.users||res.data.users||res.users||[])}catch(e){setError(e.response?.data?.detail||'โหลดรายชื่อผู้ใช้ไม่สำเร็จ')}finally{setLoading(false)}
  }

  const createUser=async(e)=>{
    e.preventDefault();setError('');setSuccess('');
    if(!username||!password){setError('กรอกให้ครบ');return}
    try{
      const res=await api.post('/admin/users',{username,password,role,max_level:level})
      setSuccess('สร้างผู้ใช้สำเร็จ')
      setUsername('');setPassword('');setRole('USER');setLevel('PUBLIC');
      load()
    }catch(err){setError(err.response?.data?.detail||'สร้างไม่สำเร็จ')}
  }

  return <div style={styles.container}>
    <h1 style={styles.title}>👤 User Management</h1>
    {error && <div style={styles.error}>❌ {error}</div>}
    {success && <div style={styles.success}>✅ {success}</div>}
    <div style={styles.section}>
      <form onSubmit={createUser}>
        <label style={styles.label}>Username</label>
        <input style={styles.input} value={username} onChange={e=>setUsername(e.target.value)} />
        <label style={styles.label}>Password</label>
        <input type='password' style={styles.input} value={password} onChange={e=>setPassword(e.target.value)} />
        <label style={styles.label}>Role</label>
        <select style={styles.select} value={role} onChange={e=>setRole(e.target.value)}>
          <option value='USER'>USER</option>
          <option value='STAFF'>STAFF</option>
          <option value='ANALYST'>ANALYST</option>
          <option value='ADMIN'>ADMIN</option>
        </select>
        <label style={styles.label}>Max Level</label>
        <select style={styles.select} value={level} onChange={e=>setLevel(e.target.value)}>
          <option value='PUBLIC'>PUBLIC</option>
          <option value='INTERNAL'>INTERNAL</option>
          <option value='CONFIDENTIAL'>CONFIDENTIAL</option>
          <option value='SECRET'>SECRET</option>
        </select>
        <button style={styles.button} type='submit'>➕ Create User</button>
      </form>
    </div>
    <div style={styles.section}>
      <h2 style={{fontSize:'18px',marginBottom:'10px',color:'#1e40af'}}>Users ({users.length})</h2>
      {loading? <div>กำลังโหลด...</div> : (
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>ID</th>
              <th style={styles.th}>Username</th>
              <th style={styles.th}>Role</th>
              <th style={styles.th}>Max Level</th>
              <th style={styles.th}>Created</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u=> <tr key={u.id}>
              <td style={styles.td}>{u.id}</td>
              <td style={styles.td}>{u.username}</td>
              <td style={styles.td}><span style={styles.badge}>{u.role}</span></td>
              <td style={styles.td}><span style={{...styles.badge, background:'#fee2e2', color:'#7f1d1d'}}>{u.max_level}</span></td>
              <td style={styles.td}>{u.created_at? new Date(u.created_at).toLocaleString('th-TH') : '-'}</td>
            </tr>)}
          </tbody>
        </table>
      )}
    </div>
  </div>
}