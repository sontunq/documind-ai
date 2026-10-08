import {
  BoundingBox,
  DocumentType,
  ExtractedFieldItem,
  IDPReviewDocument,
  QueueDocumentItem,
} from '../types/idp'

export function detectDocumentType(filename: string): DocumentType {
  const lower = filename.toLowerCase()
  if (
    lower.includes('inv') ||
    lower.includes('bill') ||
    lower.includes('receipt') ||
    lower.includes('hoa-don') ||
    lower.includes('voucher')
  ) {
    return 'invoice'
  }
  if (
    lower.includes('contract') ||
    lower.includes('ctr') ||
    lower.includes('agreement') ||
    lower.includes('hop-dong') ||
    lower.includes('mou') ||
    lower.includes('nda') ||
    lower.includes('msa')
  ) {
    return 'contract'
  }
  return 'form'
}

export function synthesizeReviewDocument(
  qDoc: Partial<QueueDocumentItem> & { id: string; filename: string },
): IDPReviewDocument {
  const docType = qDoc.predictedType || detectDocumentType(qDoc.filename)
  const lower = qDoc.filename.toLowerCase()
  const cleanBaseName = qDoc.filename
    .replace(/\.[^/.]+$/, '')
    .replace(/[_-]+/g, ' ')
    .trim()

  const fields: ExtractedFieldItem[] = []
  const boundingBoxes: BoundingBox[] = []

  const addFieldWithBox = (
    key: string,
    labelEn: string,
    labelVi: string,
    value: string,
    category: 'header' | 'parties' | 'financials' | 'dates' | 'general',
    boxCoord: { x: number; y: number; width: number; height: number },
    confidence: number = 0.95,
  ) => {
    const boxId = `box-${key}-${qDoc.id}`
    boundingBoxes.push({
      id: boxId,
      fieldKey: key,
      label: labelEn,
      x: boxCoord.x,
      y: boxCoord.y,
      width: boxCoord.width,
      height: boxCoord.height,
      confidence,
      text: value,
      page: 1,
    })
    fields.push({
      key,
      labelEn,
      labelVi,
      originalValue: value,
      correctedValue: value,
      confidence,
      boundingBoxId: boxId,
      isModified: false,
      category,
    })
  }

  if (docType === 'invoice') {
    addFieldWithBox(
      'invoice_number',
      'Invoice Number',
      'Số hóa đơn',
      `INV-2024-${Math.floor(1000 + Math.random() * 9000)}`,
      'header',
      { x: 0.65, y: 0.11, width: 0.28, height: 0.045 },
      0.98,
    )
    addFieldWithBox(
      'supplier',
      'Vendor / Supplier',
      'Đơn vị bán hàng',
      cleanBaseName.includes(' ') ? cleanBaseName : 'Apex Global Logistics Inc.',
      'parties',
      { x: 0.08, y: 0.08, width: 0.38, height: 0.05 },
      0.96,
    )
    addFieldWithBox(
      'customer',
      'Customer / Bill To',
      'Đơn vị mua hàng',
      'OmniTech Solutions Corp.',
      'parties',
      { x: 0.08, y: 0.22, width: 0.35, height: 0.045 },
      0.94,
    )
    addFieldWithBox(
      'issue_date',
      'Issue Date',
      'Ngày lập hóa đơn',
      '2024-10-15',
      'dates',
      { x: 0.65, y: 0.165, width: 0.25, height: 0.038 },
      0.95,
    )
    addFieldWithBox(
      'due_date',
      'Payment Due Date',
      'Hạn thanh toán',
      '2024-11-15',
      'dates',
      { x: 0.65, y: 0.21, width: 0.25, height: 0.038 },
      0.92,
    )
    addFieldWithBox(
      'subtotal',
      'Subtotal Amount',
      'Tổng tiền trước thuế',
      '$14,250.00',
      'financials',
      { x: 0.62, y: 0.68, width: 0.3, height: 0.038 },
      0.93,
    )
    addFieldWithBox(
      'tax',
      'Tax / VAT (8%)',
      'Tiền thuế GTGT',
      '$1,140.00',
      'financials',
      { x: 0.62, y: 0.725, width: 0.3, height: 0.038 },
      0.78,
    )
    addFieldWithBox(
      'total',
      'Total Net Amount',
      'Tổng cộng thanh toán',
      '$15,390.00',
      'financials',
      { x: 0.62, y: 0.772, width: 0.3, height: 0.045 },
      0.99,
    )
    addFieldWithBox(
      'currency',
      'Currency',
      'Đơn vị tiền tệ',
      'USD',
      'financials',
      { x: 0.54, y: 0.772, width: 0.08, height: 0.045 },
      0.68,
    )
  } else if (docType === 'contract') {
    addFieldWithBox(
      'contract_number',
      'Contract ID',
      'Số hợp đồng',
      `CTR-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}-MSA`,
      'header',
      { x: 0.3, y: 0.12, width: 0.4, height: 0.04 },
      0.94,
    )
    addFieldWithBox(
      'title',
      'Contract Title',
      'Tiêu đề hợp đồng',
      cleanBaseName.toUpperCase(),
      'header',
      { x: 0.12, y: 0.06, width: 0.76, height: 0.055 },
      0.96,
    )
    addFieldWithBox(
      'party_a',
      'Party A',
      'Bên A (Nhà cung cấp)',
      'Synthetix AI Laboratories, Inc.',
      'parties',
      { x: 0.12, y: 0.23, width: 0.45, height: 0.045 },
      0.92,
    )
    addFieldWithBox(
      'party_b',
      'Party B',
      'Bên B (Khách hàng)',
      'Nexus Enterprise Holdings LLC',
      'parties',
      { x: 0.12, y: 0.33, width: 0.45, height: 0.045 },
      0.88,
    )
    addFieldWithBox(
      'effective_date',
      'Effective Date',
      'Ngày có hiệu lực',
      '2024-11-01',
      'dates',
      { x: 0.6, y: 0.45, width: 0.25, height: 0.038 },
      0.93,
    )
    addFieldWithBox(
      'expiry_date',
      'Expiration Date',
      'Ngày hết hạn',
      '2026-10-31',
      'dates',
      { x: 0.6, y: 0.495, width: 0.25, height: 0.038 },
      0.84,
    )
    addFieldWithBox(
      'contract_value',
      'Contract Value',
      'Giá trị hợp đồng',
      '$480,000.00 USD',
      'financials',
      { x: 0.6, y: 0.55, width: 0.32, height: 0.042 },
      0.91,
    )
    addFieldWithBox(
      'governing_law',
      'Governing Law',
      'Luật điều chỉnh',
      'State of Delaware, USA',
      'general',
      { x: 0.12, y: 0.65, width: 0.48, height: 0.038 },
      0.65,
    )
  } else {
    // FORM: Distinguish Employee Form vs Tax Form vs Generic Form
    const isEmployee =
      lower.includes('employee') ||
      lower.includes('hr') ||
      lower.includes('staff') ||
      lower.includes('personnel') ||
      lower.includes('thong-tin') ||
      lower.includes('nv') ||
      lower.includes('nhan-su')
    const isTax = lower.includes('w9') || lower.includes('w4') || lower.includes('tax') || lower.includes('thue')

    if (isEmployee) {
      addFieldWithBox(
        'form_title',
        'Form Title',
        'Tiêu đề biểu mẫu',
        'EMPLOYEE INFORMATION FORM',
        'header',
        { x: 0.15, y: 0.07, width: 0.7, height: 0.045 },
        0.99,
      )
      addFieldWithBox(
        'full_name',
        'Full Name',
        'Họ và tên',
        'Nguyễn Văn An',
        'parties',
        { x: 0.09, y: 0.18, width: 0.5, height: 0.035 },
        0.96,
      )
      addFieldWithBox(
        'gender',
        'Gender',
        'Giới tính',
        'Male',
        'general',
        { x: 0.65, y: 0.18, width: 0.25, height: 0.035 },
        0.94,
      )
      addFieldWithBox(
        'date_of_birth',
        'Date of Birth',
        'Ngày sinh',
        '1994-08-15',
        'dates',
        { x: 0.09, y: 0.22, width: 0.38, height: 0.035 },
        0.95,
      )
      addFieldWithBox(
        'place_of_birth',
        'Place of Birth',
        'Nơi sinh',
        'Hà Nội, Việt Nam',
        'general',
        { x: 0.52, y: 0.22, width: 0.38, height: 0.035 },
        0.91,
      )
      addFieldWithBox(
        'id_number',
        'ID / Passport No.',
        'Số CCCD / Hộ chiếu',
        '001094002819',
        'general',
        { x: 0.09, y: 0.26, width: 0.38, height: 0.035 },
        0.97,
      )
      addFieldWithBox(
        'marital_status',
        'Marital Status',
        'Tình trạng hôn nhân',
        'Single',
        'general',
        { x: 0.09, y: 0.3, width: 0.4, height: 0.035 },
        0.89,
      )
      addFieldWithBox(
        'permanent_address',
        'Permanent Address',
        'Địa chỉ thường trú',
        '128 Cầu Giấy, P. Dịch Vọng, Q. Cầu Giấy, Hà Nội',
        'general',
        { x: 0.09, y: 0.4, width: 0.78, height: 0.035 },
        0.93,
      )
      addFieldWithBox(
        'mobile_phone',
        'Mobile Phone',
        'Số điện thoại di động',
        '+84 912 345 678',
        'general',
        { x: 0.09, y: 0.47, width: 0.38, height: 0.035 },
        0.98,
      )
      addFieldWithBox(
        'personal_email',
        'Personal Email',
        'Email cá nhân',
        'an.nguyen@example.com',
        'general',
        { x: 0.52, y: 0.47, width: 0.4, height: 0.035 },
        0.92,
      )
      addFieldWithBox(
        'position',
        'Appointed Position',
        'Vị trí bổ nhiệm',
        'Senior AI Engineer',
        'general',
        { x: 0.09, y: 0.58, width: 0.4, height: 0.035 },
        0.96,
      )
      addFieldWithBox(
        'department',
        'Department',
        'Phòng ban',
        'AI Solutions & IDP Lab',
        'general',
        { x: 0.52, y: 0.58, width: 0.4, height: 0.035 },
        0.94,
      )
      addFieldWithBox(
        'start_date',
        'Available Start Date',
        'Ngày bắt đầu công việc',
        '2026-11-01',
        'dates',
        { x: 0.09, y: 0.63, width: 0.38, height: 0.035 },
        0.91,
      )
    } else if (isTax) {
      addFieldWithBox(
        'form_title',
        'Form Title',
        'Tiêu đề biểu mẫu',
        'Form W-9: Request for Taxpayer Identification Number',
        'header',
        { x: 0.08, y: 0.06, width: 0.84, height: 0.06 },
        0.97,
      )
      addFieldWithBox(
        'entity_name',
        'Entity / Legal Name',
        'Tên pháp nhân',
        'Starlight Technologies LLC',
        'parties',
        { x: 0.08, y: 0.17, width: 0.52, height: 0.045 },
        0.95,
      )
      addFieldWithBox(
        'business_name',
        'DBA / Trade Name',
        'Tên thương mại',
        'Starlight Cloud Solutions',
        'parties',
        { x: 0.08, y: 0.24, width: 0.48, height: 0.042 },
        0.88,
      )
      addFieldWithBox(
        'tax_classification',
        'Tax Classification',
        'Phân loại thuế',
        'Limited Liability Company (LLC)',
        'general',
        { x: 0.08, y: 0.32, width: 0.45, height: 0.045 },
        0.92,
      )
      addFieldWithBox(
        'ein_number',
        'Employer Identification (EIN)',
        'Mã số thuế / EIN',
        '84-9128374',
        'general',
        { x: 0.55, y: 0.62, width: 0.35, height: 0.048 },
        0.96,
      )
      addFieldWithBox(
        'exemption_code',
        'Exemption Payee Code',
        'Mã miễn trừ khấu trừ',
        'Code 4 (Exempt)',
        'general',
        { x: 0.72, y: 0.32, width: 0.2, height: 0.045 },
        0.58,
      )
    } else {
      // General form (application, registration, requisition, etc.)
      addFieldWithBox(
        'form_title',
        'Form Title',
        'Tiêu đề biểu mẫu',
        cleanBaseName.toUpperCase(),
        'header',
        { x: 0.1, y: 0.06, width: 0.8, height: 0.05 },
        0.97,
      )
      addFieldWithBox(
        'applicant_name',
        'Applicant / Submitter Name',
        'Người nộp đơn / Đại diện',
        'Trần Đình Hoàng',
        'parties',
        { x: 0.1, y: 0.18, width: 0.45, height: 0.04 },
        0.94,
      )
      addFieldWithBox(
        'submission_date',
        'Submission Date',
        'Ngày nộp hồ sơ',
        new Date().toISOString().slice(0, 10),
        'dates',
        { x: 0.6, y: 0.18, width: 0.3, height: 0.04 },
        0.95,
      )
      addFieldWithBox(
        'id_number',
        'Identification / Ref ID',
        'Số định danh / Mã hồ sơ',
        `REG-${Math.floor(100000 + Math.random() * 900000)}`,
        'general',
        { x: 0.1, y: 0.28, width: 0.4, height: 0.04 },
        0.92,
      )
      addFieldWithBox(
        'contact_number',
        'Contact Phone',
        'Số điện thoại liên hệ',
        '+84 988 765 432',
        'general',
        { x: 0.55, y: 0.28, width: 0.35, height: 0.04 },
        0.96,
      )
      addFieldWithBox(
        'email_address',
        'Email Address',
        'Địa chỉ Email',
        'contact@documind.ai',
        'general',
        { x: 0.1, y: 0.38, width: 0.45, height: 0.04 },
        0.91,
      )
      addFieldWithBox(
        'department',
        'Target Department',
        'Bộ phận tiếp nhận',
        'Administration & Processing',
        'general',
        { x: 0.55, y: 0.38, width: 0.35, height: 0.04 },
        0.89,
      )
      addFieldWithBox(
        'request_purpose',
        'Request Purpose',
        'Mục đích / Nội dung yêu cầu',
        'Official Verification & Record Archival',
        'general',
        { x: 0.1, y: 0.5, width: 0.8, height: 0.06 },
        0.87,
      )
    }
  }

  return {
    id: qDoc.id,
    filename: qDoc.filename,
    mediaType: qDoc.mediaType || 'application/pdf',
    sizeBytes: qDoc.sizeBytes || 245000,
    createdAt: qDoc.uploadedAt || new Date().toISOString(),
    status: 'AWAITING_REVIEW',
    pageCount: qDoc.pageCount || 1,
    currentPage: 1,
    fileUrl: qDoc.fileUrl,
    backendId: qDoc.backendId,
    classification: {
      predictedType: docType,
      confidence: qDoc.confidence || 0.94,
      threshold: 0.85,
      modelIdentifier: 'documind-layoutlm-hybrid-v2',
      modelVersion: '2.4.0',
      scores: {
        invoice: docType === 'invoice' ? 0.94 : 0.03,
        contract: docType === 'contract' ? 0.94 : 0.03,
        form: docType === 'form' ? 0.94 : 0.03,
      },
    },
    fields,
    boundingBoxes,
  }
}
