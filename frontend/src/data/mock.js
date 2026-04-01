export const MOCK_DATA = {
  waves: [["AppC","AppD"],["AppB"],["AppA"]],
  risk: { AppA:"High", AppB:"Medium", AppC:"High", AppD:"Low" },
  strategy: { AppA:"Refactor", AppB:"Replatform", AppC:"Refactor", AppD:"Rehost" },
  timeline: { AppA:"4-5 days", AppB:"2-3 days", AppC:"4-5 days", AppD:"1-2 days" },
  dependencies: { AppA:["AppB"], AppB:["AppC"], AppC:[], AppD:[] },
  explanation: "AppC and AppD have no dependencies so they migrate first in Wave 1. AppB depends on AppC so it moves in Wave 2. AppA is highest risk (Refactor strategy) and migrates last in Wave 3 after its dependencies are stable."
};
