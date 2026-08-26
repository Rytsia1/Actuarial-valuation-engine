import dagre from 'dagre'

/**
 * Compute auto-layout using Dagre graph layout engine.
 *
 * @param {Array} nodes
 * @param {Array} edges
 * @param {string} direction - 'LR' (Left-to-Right) or 'TB' (Top-to-Bottom)
 * @returns {Object} { nodes, edges } with computed positions
 */
export function layoutGraph(nodes, edges, direction = 'LR') {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))

  const nodeWidth = 260
  const nodeHeight = 180

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 40,
    ranksep: 70,
    marginx: 30,
    marginy: 30,
  })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    }
  })

  return { nodes: layoutedNodes, edges }
}

// ────────────────────────────────────────────────────────────
// Product Preset Graph Templates
// ────────────────────────────────────────────────────────────

export const PRESET_TEMPLATES = {
  term_life_20y: {
    id: 'term_life_20y',
    name: '20-Year Term Life',
    badge: 'Protection',
    description: 'Level premium mortality protection with 100% death benefit outgo.',
    nodes: [
      {
        id: 'node-policy-input',
        type: 'policyInput',
        data: {
          product_name: '20-Year Term Life',
          age: 35,
          term: 20,
          sum_assured: 1000000,
          premium_freq: 'annual',
          interest_rate: 0.05,
          table_id: 'soa_ilt',
        },
      },
      {
        id: 'node-inflow-premium',
        type: 'inflow',
        data: {
          inflow_type: 'Gross Premium',
          mode: 'formula',
          amount: 0,
          frequency: 'annual',
        },
      },
      {
        id: 'node-contingency-mortality',
        type: 'contingency',
        data: {
          decrement_type: 'Mortality',
          table_id: 'soa_ilt',
          multiplier: 1.0,
          lapse_rate: 0.03,
        },
      },
      {
        id: 'node-outflow-death',
        type: 'outflow',
        data: {
          benefit_type: 'Death Benefit',
          formula: '1.0 * SA',
          factor: 1.0,
        },
      },
      {
        id: 'node-outflow-expense',
        type: 'outflow',
        data: {
          benefit_type: 'Expense Loadings',
          formula: '35% Y1 / 5% Ren',
          first_year_pct: 0.35,
          renewal_pct: 0.05,
        },
      },
      {
        id: 'node-valuation-sink',
        type: 'valuationSink',
        data: {
          label: 'Valuation Consolidator',
        },
      },
    ],
    edges: [
      {
        id: 'e-policy-inflow',
        source: 'node-policy-input',
        target: 'node-inflow-premium',
        sourceHandle: 'policy_meta',
        targetHandle: 'inflow_in',
        animated: true,
      },
      {
        id: 'e-policy-contingency',
        source: 'node-policy-input',
        target: 'node-contingency-mortality',
        sourceHandle: 'policy_meta',
        targetHandle: 'contingency_in',
        animated: true,
      },
      {
        id: 'e-contingency-death',
        source: 'node-contingency-mortality',
        target: 'node-outflow-death',
        sourceHandle: 'on_death',
        targetHandle: 'outflow_in',
        animated: true,
      },
      {
        id: 'e-inflow-expense',
        source: 'node-inflow-premium',
        target: 'node-outflow-expense',
        sourceHandle: 'cash_inflow',
        targetHandle: 'outflow_in',
      },
      {
        id: 'e-inflow-sink',
        source: 'node-inflow-premium',
        target: 'node-valuation-sink',
        sourceHandle: 'cash_inflow',
        targetHandle: 'sink_inflow',
        animated: true,
      },
      {
        id: 'e-death-sink',
        source: 'node-outflow-death',
        target: 'node-valuation-sink',
        sourceHandle: 'cash_outflow',
        targetHandle: 'sink_outflow',
        animated: true,
      },
      {
        id: 'e-expense-sink',
        source: 'node-outflow-expense',
        target: 'node-valuation-sink',
        sourceHandle: 'cash_outflow',
        targetHandle: 'sink_outflow',
      },
    ],
  },

  endowment_15y: {
    id: 'endowment_15y',
    name: '15-Year Endowment',
    badge: 'Savings & Protection',
    description: 'Dual benefit structure: Death benefit on death or 100% Sum Assured on survival at year 15.',
    nodes: [
      {
        id: 'node-policy-input',
        type: 'policyInput',
        data: {
          product_name: '15-Year Endowment',
          age: 30,
          term: 15,
          sum_assured: 500000,
          premium_freq: 'annual',
          interest_rate: 0.045,
          table_id: 'soa_ilt',
        },
      },
      {
        id: 'node-inflow-premium',
        type: 'inflow',
        data: {
          inflow_type: 'Gross Premium',
          mode: 'formula',
          amount: 0,
        },
      },
      {
        id: 'node-contingency',
        type: 'contingency',
        data: {
          decrement_type: 'Mortality + Maturity',
          table_id: 'soa_ilt',
          multiplier: 1.0,
          lapse_rate: 0.02,
        },
      },
      {
        id: 'node-outflow-death',
        type: 'outflow',
        data: {
          benefit_type: 'Death Benefit',
          formula: '1.0 * SA',
          factor: 1.0,
        },
      },
      {
        id: 'node-outflow-maturity',
        type: 'outflow',
        data: {
          benefit_type: 'Maturity Benefit',
          formula: '1.0 * SA',
          factor: 1.0,
          maturity_year: 15,
        },
      },
      {
        id: 'node-outflow-expense',
        type: 'outflow',
        data: {
          benefit_type: 'Expense Loadings',
          formula: '30% Y1 / 4% Ren',
          first_year_pct: 0.30,
          renewal_pct: 0.04,
        },
      },
      {
        id: 'node-valuation-sink',
        type: 'valuationSink',
        data: {
          label: 'Endowment Valuator',
        },
      },
    ],
    edges: [
      {
        id: 'e-pol-inflow',
        source: 'node-policy-input',
        target: 'node-inflow-premium',
        sourceHandle: 'policy_meta',
        targetHandle: 'inflow_in',
        animated: true,
      },
      {
        id: 'e-pol-cont',
        source: 'node-policy-input',
        target: 'node-contingency',
        sourceHandle: 'policy_meta',
        targetHandle: 'contingency_in',
        animated: true,
      },
      {
        id: 'e-cont-death',
        source: 'node-contingency',
        target: 'node-outflow-death',
        sourceHandle: 'on_death',
        targetHandle: 'outflow_in',
        animated: true,
      },
      {
        id: 'e-cont-mat',
        source: 'node-contingency',
        target: 'node-outflow-maturity',
        sourceHandle: 'on_survival',
        targetHandle: 'outflow_in',
        animated: true,
      },
      {
        id: 'e-inflow-sink',
        source: 'node-inflow-premium',
        target: 'node-valuation-sink',
        sourceHandle: 'cash_inflow',
        targetHandle: 'sink_inflow',
        animated: true,
      },
      {
        id: 'e-death-sink',
        source: 'node-outflow-death',
        target: 'node-valuation-sink',
        sourceHandle: 'cash_outflow',
        targetHandle: 'sink_outflow',
        animated: true,
      },
      {
        id: 'e-mat-sink',
        source: 'node-outflow-maturity',
        target: 'node-valuation-sink',
        sourceHandle: 'cash_outflow',
        targetHandle: 'sink_outflow',
        animated: true,
      },
      {
        id: 'e-inflow-exp',
        source: 'node-inflow-premium',
        target: 'node-outflow-expense',
        sourceHandle: 'cash_inflow',
        targetHandle: 'outflow_in',
      },
      {
        id: 'e-exp-sink',
        source: 'node-outflow-expense',
        target: 'node-valuation-sink',
        sourceHandle: 'cash_outflow',
        targetHandle: 'sink_outflow',
      },
    ],
  },

  unit_linked_base: {
    id: 'unit_linked_base',
    name: 'Unit-Linked / Universal Life',
    badge: 'Investment-Linked',
    description: 'Flexible premium accumulation with mortality Cost of Insurance (COI) charges and fund value payouts.',
    nodes: [
      {
        id: 'node-policy-input',
        type: 'policyInput',
        data: {
          product_name: 'Universal Investment Life',
          age: 35,
          term: 20,
          sum_assured: 750000,
          premium_freq: 'annual',
          interest_rate: 0.05,
          table_id: 'soa_ilt',
        },
      },
      {
        id: 'node-inflow-premium',
        type: 'inflow',
        data: {
          inflow_type: 'Target Premium + Top-Up',
          mode: 'fixed',
          amount: 5000,
        },
      },
      {
        id: 'node-accumulator',
        type: 'accumulator',
        data: {
          growth_rate: 0.065,
          admin_charge: 100,
          allocation_pct: 0.95,
        },
      },
      {
        id: 'node-contingency',
        type: 'contingency',
        data: {
          decrement_type: 'Mortality + Lapse',
          table_id: 'soa_ilt',
          multiplier: 1.0,
          lapse_rate: 0.04,
        },
      },
      {
        id: 'node-outflow-death',
        type: 'outflow',
        data: {
          benefit_type: 'Death Benefit (Max SA & AV)',
          formula: '1.0 * SA',
          factor: 1.0,
        },
      },
      {
        id: 'node-outflow-surrender',
        type: 'outflow',
        data: {
          benefit_type: 'Surrender Value',
          formula: 'Account Value Payout',
          surrender_ratio: 0.85,
        },
      },
      {
        id: 'node-valuation-sink',
        type: 'valuationSink',
        data: {
          label: 'Unit-Linked Consolidator',
        },
      },
    ],
    edges: [
      {
        id: 'e-ul-pol-inflow',
        source: 'node-policy-input',
        target: 'node-inflow-premium',
        sourceHandle: 'policy_meta',
        targetHandle: 'inflow_in',
        animated: true,
      },
      {
        id: 'e-ul-inflow-acc',
        source: 'node-inflow-premium',
        target: 'node-accumulator',
        sourceHandle: 'cash_inflow',
        targetHandle: 'acc_inflow',
        animated: true,
      },
      {
        id: 'e-ul-pol-cont',
        source: 'node-policy-input',
        target: 'node-contingency',
        sourceHandle: 'policy_meta',
        targetHandle: 'contingency_in',
        animated: true,
      },
      {
        id: 'e-ul-cont-death',
        source: 'node-contingency',
        target: 'node-outflow-death',
        sourceHandle: 'on_death',
        targetHandle: 'outflow_in',
        animated: true,
      },
      {
        id: 'e-ul-cont-surr',
        source: 'node-contingency',
        target: 'node-outflow-surrender',
        sourceHandle: 'on_lapse',
        targetHandle: 'outflow_in',
        animated: true,
      },
      {
        id: 'e-ul-inflow-sink',
        source: 'node-inflow-premium',
        target: 'node-valuation-sink',
        sourceHandle: 'cash_inflow',
        targetHandle: 'sink_inflow',
        animated: true,
      },
      {
        id: 'e-ul-death-sink',
        source: 'node-outflow-death',
        target: 'node-valuation-sink',
        sourceHandle: 'cash_outflow',
        targetHandle: 'sink_outflow',
        animated: true,
      },
      {
        id: 'e-ul-surr-sink',
        source: 'node-outflow-surrender',
        target: 'node-valuation-sink',
        sourceHandle: 'cash_outflow',
        targetHandle: 'sink_outflow',
        animated: true,
      },
    ],
  },

  blank_canvas: {
    id: 'blank_canvas',
    name: 'Blank Canvas',
    badge: 'Custom',
    description: 'Start with an empty blueprint canvas and drag custom nodes from the sidebar.',
    nodes: [
      {
        id: 'node-policy-input',
        type: 'policyInput',
        data: {
          product_name: 'New Custom Product',
          age: 35,
          term: 20,
          sum_assured: 1000000,
          premium_freq: 'annual',
          interest_rate: 0.05,
          table_id: 'soa_ilt',
        },
      },
    ],
    edges: [],
  },
}
