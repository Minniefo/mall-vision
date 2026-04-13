import React, { useEffect, useState, useMemo } from "react";
import axios from "axios";
import { Bar } from "react-chartjs-2";
import { Chart as ChartJS, BarElement, CategoryScale, LinearScale, Tooltip, Legend } from "chart.js";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function AgeGenderChart(){

 const [rows,setRows] = useState([]);

 useEffect(()=>{
   axios.get(`${API_BASE}/analytics/age-gender-distribution`)
   .then(res=>setRows(res.data||[]));
 },[]);

 const {labels,male,female} = useMemo(()=>{

   const ageGroups=["1-12","13-19","20-35","36+"];

   const maleMap={}
   const femaleMap={}

   rows.forEach(r=>{
     const age=r._id.age_group
     const gender=r._id.gender
     const count=r.count

     if(gender==="male") maleMap[age]=count
     if(gender==="female") femaleMap[age]=count
   })

   return{
     labels:ageGroups,
     male:ageGroups.map(a=>maleMap[a]||0),
     female:ageGroups.map(a=>femaleMap[a]||0)
   }

 },[rows])

 const data={
   labels,
   datasets:[
     {label:"Male",data:male,backgroundColor:"#2196F3"},
     {label:"Female",data:female,backgroundColor:"#E91E63"}
   ]
 }

 return(
   <div style={{height:320}}>
     <h3>Age & Gender Distribution</h3>
     <Bar data={data}/>
   </div>
 )

}