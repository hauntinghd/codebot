// Minimal provider balance module — in-memory for MVP but pluggable
let balanceUsd = Number(process.env.XAI_BALANCE_USD || 100);

export function getBalance() { return balanceUsd; }
export function reduce(amount:number) { balanceUsd = Math.max(0, balanceUsd - amount); return balanceUsd; }
export function setBalance(v:number) { balanceUsd = v; }
