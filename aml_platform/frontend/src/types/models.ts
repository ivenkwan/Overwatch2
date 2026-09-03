// 1. Channel Dimension
export interface Channel {
  id: string;
  type: 'SWIFT' | 'ERC-20' | 'FIAT' | 'INTERNAL' | 'WALLET';
  identifier: string; // e.g., IBAN, Wallet Address
  institution: string; // e.g., Bank Name, VASP Name, or "On-chain"
  jurisdiction: string;
  riskRating: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

// 2. Customer Dimension
export interface Customer {
  id: string;
  name: string;
  type: 'INDIVIDUAL' | 'CORPORATE';
  businessNature?: string; // For corporates
  occupation?: string; // For individuals
  onboardDate: string;
  cddStatus: 'CLEared' | 'PENDING' | 'OVERDUE' | 'RESTRICTED';
  riskRating: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  sourceOfWealth: string;
  jurisdictions: string[]; // e.g., Operating countries or residencies
  channels: Channel[]; // Linked accounts and wallets
}

// 3. Payment Dimension
export interface Payment {
  id: string;
  timestamp: string;
  amountUsd: number;
  currency: string;
  originalAmount: number;
  sourceChannelId: string;
  destinationChannelId: string;
  status: 'PENDING' | 'CLEARED' | 'BLOCKED' | 'REFUNDED';
  typologyTags: string[]; // e.g., ['RAPID_MOVEMENT', 'CROSS_BORDER']
}

// 4. Alert Dimension
export interface Alert {
  id: string;
  createdAt: string;
  customerId: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  type: 'BEHAVIORAL' | 'SCREENING' | 'TRANSACTIONAL';
  triggerScenario: string; // e.g., "Structuring/smurfing below threshold bands"
  score: number; // 0-100
  status: 'NEW' | 'IN_REVIEW' | 'ESCALATED' | 'CLOSED';
  relatedPayments: string[]; // Array of Payment IDs
  analystRationale?: string;
}

// 5. Case Dimension
export interface Case {
  case_id: string;
  case_number: string;
  created_at: string;
  status: string;
  severity: string;
  source_alert_id?: string;
  created_by: string;
  assigned_to?: string;
  reviewer_id?: string;
  approver_id?: string;
  workflow_instance_id?: string;
  activeTask?: {
    id: string;
    name: string;
    assignee: string | null;
    taskDefinitionKey: string;
  };
}
