import { useEffect, useState } from 'react'
import api from '../lib/api'
import { useLanguage } from '../contexts/LanguageContext'

interface CalcType {
  type: string
  name: string
  inputs: string[]
}

interface Result {
  formula: string
  steps: string[]
  result: number
  explanation: string
}

export default function CalculatorPage() {
  const { t } = useLanguage()
  const [types, setTypes] = useState<CalcType[]>([])
  const [selected, setSelected] = useState('')
  const [inputs, setInputs] = useState<Record<string, string>>({})
  const [result, setResult] = useState<Result | null>(null)

  useEffect(() => {
    api.get('/calculator/types').then(({ data }) => {
      setTypes(data)
      if (data.length) setSelected(data[0].type)
    })
  }, [])

  const current = types.find((t) => t.type === selected)

  const calculate = async () => {
    const numericInputs: Record<string, number> = {}
    current?.inputs.forEach((key) => { numericInputs[key] = parseFloat(inputs[key] || '0') })
    const { data } = await api.post('/calculator/calculate', {
      calculation_type: selected,
      inputs: numericInputs,
    })
    setResult(data)
  }

  return (
    <div className="page">
      <header className="page-header"><h2>{t('poultry_calculator')}</h2></header>
      <div className="calculator-layout">
        <div className="chart-card">
          <div className="form-group">
            <label>{t('calculation')}</label>
            <select value={selected} onChange={(e) => { setSelected(e.target.value); setResult(null) }}>
              {types.map((ct) => <option key={ct.type} value={ct.type}>{ct.name}</option>)}
            </select>
          </div>
          {current?.inputs.map((key) => (
            <div key={key} className="form-group">
              <label>{key.replace(/_/g, ' ')}</label>
              <input type="number" value={inputs[key] || ''} onChange={(e) => setInputs({ ...inputs, [key]: e.target.value })} />
            </div>
          ))}
          <button className="btn-primary" onClick={calculate}>{t('calculate')}</button>
        </div>
        {result && (
          <div className="chart-card result-card">
            <h3>{t('result')}: {result.result}</h3>
            <p className="formula">{result.formula}</p>
            <ol>{result.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
            <p className="explanation">{result.explanation}</p>
          </div>
        )}
      </div>
    </div>
  )
}
