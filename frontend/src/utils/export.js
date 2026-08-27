export function exportValuationCSV(deterministicData, formParams) {
  if (!deterministicData || !deterministicData.reserve_profile) {
    console.warn('No deterministic data available to export.')
    return
  }

  const profile = deterministicData.reserve_profile
  const p = formParams

  // CSV Headers
  let csvContent = "Duration (t),lx,dx,Premium Income,Death Benefits,Endowment Benefits,Expenses,Prospective Reserve,Retrospective Reserve,Gross GPV,Discounted Cash Flows\n"

  // Rows
  profile.forEach(row => {
    const data = [
      row.duration,
      row.lx || 0,
      row.dx || 0,
      row.premium_income || 0,
      row.death_benefits || 0,
      row.endowment_benefits || 0,
      row.expenses || 0,
      row.reserve_prospective || 0,
      row.reserve_retrospective || 0,
      row.gross_reserve || 0,
      row.discounted_cash_flows || 0
    ]
    csvContent += data.join(",") + "\n"
  })

  // Create Blob and Download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement("a")
  const timestamp = new Date().toISOString().slice(0,19).replace(/[:T]/g, "-")
  const filename = `valuation_export_${p.product_type}_age${p.issue_age}_${timestamp}.csv`
  
  link.setAttribute("href", url)
  link.setAttribute("download", filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
