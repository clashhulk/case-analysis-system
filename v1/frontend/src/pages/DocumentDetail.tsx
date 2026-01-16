import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Download,
  FileText,
  Save,
  Pencil,
  Plus,
  Trash2,
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertCircle,
  Calendar,
  MapPin,
  Users,
  Building,
  FileDigit,
  Clock
} from 'lucide-react';
import { documentsApi } from '@/api/client';
import PdfViewer from '@/components/document/PdfViewer';
import type {
  AnalysisUpdateRequest,
  PersonEntity,
  AnnotationCreate
} from '@/types';

// Helper to download blob
const downloadBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

export default function DocumentDetail() {
  const { caseId, documentId } = useParams<{ caseId: string; documentId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // UI State
  const [activeTab, setActiveTab] = useState<'viewer' | 'analysis'>('viewer');
  const [isEditing, setIsEditing] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);

  // Expanded sections state
  const [expandedSections, setExpandedSections] = useState({
    summary: true,
    people: true,
    dates: true,
    locations: true,
    caseNumbers: true,
    organizations: true,
    timeline: true
  });

  // Edit state
  const [editedSummary, setEditedSummary] = useState('');
  const [editedClassification, setEditedClassification] = useState('');
  const [editedKeyPoints, setEditedKeyPoints] = useState<string[]>([]);
  const [editedPeople, setEditedPeople] = useState<PersonEntity[]>([]);
  const [editedDates, setEditedDates] = useState<string[]>([]);
  const [editedLocations, setEditedLocations] = useState<string[]>([]);
  const [editedCaseNumbers, setEditedCaseNumbers] = useState<string[]>([]);
  const [editedOrganizations, setEditedOrganizations] = useState<string[]>([]);

  // Fetch document details
  const { data: document, isLoading: documentLoading } = useQuery({
    queryKey: ['document', caseId, documentId],
    queryFn: () => documentsApi.get(caseId!, documentId!),
    enabled: !!caseId && !!documentId
  });

  // Fetch analysis
  const { data: analysis, isLoading: analysisLoading } = useQuery({
    queryKey: ['document-analysis', caseId, documentId],
    queryFn: () => documentsApi.getAnalysis(caseId!, documentId!),
    enabled: !!caseId && !!documentId
  });

  // Fetch preview URL
  const { data: previewUrl, isLoading: previewLoading } = useQuery({
    queryKey: ['document-preview', caseId, documentId],
    queryFn: () => documentsApi.getPreviewUrl(caseId!, documentId!),
    enabled: !!caseId && !!documentId
  });

  // Fetch annotations
  const { data: annotations = [] } = useQuery({
    queryKey: ['document-annotations', caseId, documentId],
    queryFn: () => documentsApi.getAnnotations(caseId!, documentId!),
    enabled: !!caseId && !!documentId
  });

  // Initialize edit state when analysis loads
  useEffect(() => {
    if (analysis?.analysis) {
      setEditedSummary(analysis.analysis.summary || '');
      setEditedClassification(analysis.analysis.classification || '');
      setEditedKeyPoints(analysis.analysis.key_points || []);
    }
    if (analysis?.entities) {
      setEditedPeople(analysis.entities.people || []);
      setEditedDates(analysis.entities.dates || []);
      setEditedLocations(analysis.entities.locations || []);
      setEditedCaseNumbers(analysis.entities.case_numbers || []);
      setEditedOrganizations(analysis.entities.organizations || []);
    }
  }, [analysis]);

  // Update analysis mutation
  const updateMutation = useMutation({
    mutationFn: (data: AnalysisUpdateRequest) =>
      documentsApi.updateAnalysis(caseId!, documentId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-analysis', caseId, documentId] });
      setIsEditing(false);
      setIsDirty(false);
    }
  });

  // Export mutations
  const exportDocxMutation = useMutation({
    mutationFn: () => documentsApi.exportDocx(caseId!, documentId!),
    onSuccess: (blob) => {
      const filename = document?.original_filename?.replace(/\.[^/.]+$/, '') || 'document';
      downloadBlob(blob, `${filename}_analysis.docx`);
    }
  });

  const exportMarkdownMutation = useMutation({
    mutationFn: () => documentsApi.exportMarkdown(caseId!, documentId!),
    onSuccess: (blob) => {
      const filename = document?.original_filename?.replace(/\.[^/.]+$/, '') || 'document';
      downloadBlob(blob, `${filename}_analysis.md`);
    }
  });

  // Annotation mutations with optimistic updates and cache invalidation
  const createAnnotationMutation = useMutation({
    mutationFn: (data: AnnotationCreate) =>
      documentsApi.createAnnotation(caseId!, documentId!, data),
    onSuccess: (newAnnotation) => {
      // Optimistic update: immediately show in UI
      queryClient.setQueryData(
        ['document-annotations', caseId, documentId],
        (old: any) => [...(old || []), newAnnotation]
      );
      // Refetch to ensure persistence
      queryClient.invalidateQueries({ queryKey: ['document-annotations', caseId, documentId] });
    }
  });

  const deleteAnnotationMutation = useMutation({
    mutationFn: (annotationId: string) =>
      documentsApi.deleteAnnotation(caseId!, documentId!, annotationId),
    onSuccess: (_, annotationId) => {
      // Optimistic update: immediately remove from UI
      queryClient.setQueryData(
        ['document-annotations', caseId, documentId],
        (old: any) => (old || []).filter((ann: any) => ann.id !== annotationId)
      );
      // Refetch to ensure persistence
      queryClient.invalidateQueries({ queryKey: ['document-annotations', caseId, documentId] });
    }
  });

  // Annotation handlers
  const handleCreateAnnotation = (data: AnnotationCreate) => {
    createAnnotationMutation.mutate(data);
  };

  const handleDeleteAnnotation = (annotationId: string) => {
    deleteAnnotationMutation.mutate(annotationId);
  };

  // Handle save
  const handleSave = () => {
    const updates: AnalysisUpdateRequest = {};

    if (editedSummary !== analysis?.analysis?.summary) {
      updates.summary = editedSummary;
    }
    if (editedClassification !== analysis?.analysis?.classification) {
      updates.classification = editedClassification;
    }
    if (JSON.stringify(editedKeyPoints) !== JSON.stringify(analysis?.analysis?.key_points)) {
      updates.key_points = editedKeyPoints;
    }

    // Check entities changes
    const entitiesChanged =
      JSON.stringify(editedPeople) !== JSON.stringify(analysis?.entities?.people) ||
      JSON.stringify(editedDates) !== JSON.stringify(analysis?.entities?.dates) ||
      JSON.stringify(editedLocations) !== JSON.stringify(analysis?.entities?.locations) ||
      JSON.stringify(editedCaseNumbers) !== JSON.stringify(analysis?.entities?.case_numbers) ||
      JSON.stringify(editedOrganizations) !== JSON.stringify(analysis?.entities?.organizations);

    if (entitiesChanged) {
      updates.entities = {
        people: editedPeople,
        dates: editedDates,
        locations: editedLocations,
        case_numbers: editedCaseNumbers,
        organizations: editedOrganizations
      };
    }

    updateMutation.mutate(updates);
  };

  // Cancel editing
  const handleCancel = () => {
    if (analysis?.analysis) {
      setEditedSummary(analysis.analysis.summary || '');
      setEditedClassification(analysis.analysis.classification || '');
      setEditedKeyPoints(analysis.analysis.key_points || []);
    }
    if (analysis?.entities) {
      setEditedPeople(analysis.entities.people || []);
      setEditedDates(analysis.entities.dates || []);
      setEditedLocations(analysis.entities.locations || []);
      setEditedCaseNumbers(analysis.entities.case_numbers || []);
      setEditedOrganizations(analysis.entities.organizations || []);
    }
    setIsEditing(false);
    setIsDirty(false);
  };

  // Toggle section expansion
  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Handle field change
  const markDirty = () => {
    if (!isDirty) setIsDirty(true);
    if (!isEditing) setIsEditing(true);
  };

  // Check if preview is supported
  const isPreviewSupported = () => {
    if (!document?.file_type) return false;
    const supported = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'];
    return supported.includes(document.file_type);
  };

  if (documentLoading || analysisLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!document) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900">Document not found</h2>
          <button
            onClick={() => navigate(`/cases/${caseId}/documents`)}
            className="mt-4 text-blue-600 hover:text-blue-800"
          >
            Back to Documents
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/cases/${caseId}/documents`)}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="h-5 w-5" />
            <span className="hidden sm:inline">Back to Documents</span>
          </button>
          <div className="h-6 w-px bg-gray-300" />
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-gray-400" />
            <h1 className="text-lg font-semibold text-gray-900 truncate max-w-md">
              {document.original_filename}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Save button (when editing) */}
          {isDirty && (
            <>
              <button
                onClick={handleCancel}
                className="px-3 py-1.5 text-gray-600 hover:text-gray-900"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={updateMutation.isPending}
                className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {updateMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Save Changes
              </button>
            </>
          )}

          {/* Export menu */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="flex items-center gap-2 px-4 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <Download className="h-4 w-4" />
              Export
              <ChevronDown className="h-4 w-4" />
            </button>

            {showExportMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                <button
                  onClick={() => {
                    if (previewUrl?.url) {
                      window.open(previewUrl.url, '_blank');
                    }
                    setShowExportMenu(false);
                  }}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                >
                  <Download className="h-4 w-4" />
                  Download Original
                </button>
                <button
                  onClick={() => {
                    exportDocxMutation.mutate();
                    setShowExportMenu(false);
                  }}
                  disabled={exportDocxMutation.isPending}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                >
                  <FileText className="h-4 w-4" />
                  {exportDocxMutation.isPending ? 'Exporting...' : 'Export as DOCX'}
                </button>
                <button
                  onClick={() => {
                    exportMarkdownMutation.mutate();
                    setShowExportMenu(false);
                  }}
                  disabled={exportMarkdownMutation.isPending}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                >
                  <FileText className="h-4 w-4" />
                  {exportMarkdownMutation.isPending ? 'Exporting...' : 'Export as Markdown'}
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Mobile tabs */}
      <div className="lg:hidden flex border-b border-gray-200 bg-white">
        <button
          onClick={() => setActiveTab('viewer')}
          className={`flex-1 py-3 text-sm font-medium ${
            activeTab === 'viewer'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-500'
          }`}
        >
          Document
        </button>
        <button
          onClick={() => setActiveTab('analysis')}
          className={`flex-1 py-3 text-sm font-medium ${
            activeTab === 'analysis'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-500'
          }`}
        >
          Analysis
        </button>
      </div>

      {/* Main content - Split panel */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Document Viewer */}
        <div
          className={`${
            activeTab === 'viewer' ? 'block' : 'hidden'
          } lg:block lg:w-1/2 bg-gray-100 border-r border-gray-200 flex flex-col`}
        >
          {previewLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : document.file_type === 'application/pdf' && previewUrl?.url ? (
            <PdfViewer
              url={previewUrl.url}
              annotations={annotations}
              onCreateAnnotation={handleCreateAnnotation}
              onDeleteAnnotation={handleDeleteAnnotation}
            />
          ) : isPreviewSupported() && previewUrl?.url ? (
            <div className="flex-1 overflow-auto p-4 flex justify-center">
              <img
                src={previewUrl.url}
                alt={document.original_filename}
                className="max-w-full h-auto shadow-lg"
              />
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
              <FileText className="h-16 w-16 mb-4" />
              <p className="text-lg font-medium">Preview not available</p>
              <p className="text-sm mt-1">
                {document.file_type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                  ? 'Word documents cannot be previewed'
                  : 'This file type cannot be previewed'}
              </p>
              {previewUrl?.url && (
                <button
                  onClick={() => window.open(previewUrl.url, '_blank')}
                  className="mt-4 flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  <Download className="h-4 w-4" />
                  Download to View
                </button>
              )}
            </div>
          )}
        </div>

        {/* Right Panel - Analysis */}
        <div
          className={`${
            activeTab === 'analysis' ? 'block' : 'hidden'
          } lg:block lg:w-1/2 overflow-auto bg-white`}
        >
          {!analysis?.analysis ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 p-8">
              <AlertCircle className="h-12 w-12 mb-4" />
              <p className="text-lg font-medium">No analysis available</p>
              <p className="text-sm mt-1 text-center">
                This document hasn't been analyzed yet.
                <br />
                Go back to documents and click "Analyze" to process it.
              </p>
            </div>
          ) : (
            <div className="p-6 space-y-6">
              {/* Summary Section */}
              <div className="bg-gray-50 rounded-lg p-4">
                <button
                  onClick={() => toggleSection('summary')}
                  className="flex items-center justify-between w-full"
                >
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    {expandedSections.summary ? (
                      <ChevronDown className="h-5 w-5" />
                    ) : (
                      <ChevronRight className="h-5 w-5" />
                    )}
                    Summary
                  </h3>
                  {analysis.analysis.classification && (
                    <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                      {analysis.analysis.classification}
                      {analysis.analysis.confidence && (
                        <span className="ml-1 text-blue-600">
                          ({Math.round(analysis.analysis.confidence * 100)}%)
                        </span>
                      )}
                    </span>
                  )}
                </button>

                {expandedSections.summary && (
                  <div className="mt-4 space-y-4">
                    {/* Summary text */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-sm font-medium text-gray-700">Summary</label>
                        {!isEditing && (
                          <button
                            onClick={() => setIsEditing(true)}
                            className="text-gray-400 hover:text-gray-600"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                      {isEditing ? (
                        <textarea
                          value={editedSummary}
                          onChange={(e) => {
                            setEditedSummary(e.target.value);
                            markDirty();
                          }}
                          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          rows={4}
                        />
                      ) : (
                        <p className="text-gray-700">{analysis.analysis.summary}</p>
                      )}
                    </div>

                    {/* Key Points */}
                    {(editedKeyPoints.length > 0 || isEditing) && (
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-sm font-medium text-gray-700">Key Points</label>
                          {isEditing && (
                            <button
                              onClick={() => {
                                setEditedKeyPoints([...editedKeyPoints, '']);
                                markDirty();
                              }}
                              className="text-blue-600 hover:text-blue-800 text-sm flex items-center gap-1"
                            >
                              <Plus className="h-3 w-3" /> Add
                            </button>
                          )}
                        </div>
                        <ul className="space-y-2">
                          {editedKeyPoints.map((point, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-blue-500 mt-1">•</span>
                              {isEditing ? (
                                <div className="flex-1 flex gap-2">
                                  <input
                                    value={point}
                                    onChange={(e) => {
                                      const newPoints = [...editedKeyPoints];
                                      newPoints[idx] = e.target.value;
                                      setEditedKeyPoints(newPoints);
                                      markDirty();
                                    }}
                                    className="flex-1 p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                                  />
                                  <button
                                    onClick={() => {
                                      setEditedKeyPoints(editedKeyPoints.filter((_, i) => i !== idx));
                                      markDirty();
                                    }}
                                    className="text-red-500 hover:text-red-700"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
                                </div>
                              ) : (
                                <span className="text-gray-700">{point}</span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* People Section */}
              <EntitySection
                title="People"
                icon={<Users className="h-5 w-5 text-purple-500" />}
                expanded={expandedSections.people}
                onToggle={() => toggleSection('people')}
                count={editedPeople.length}
                isEditing={isEditing}
                onStartEdit={() => setIsEditing(true)}
              >
                {editedPeople.map((person, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-2 bg-gray-50 rounded">
                    {isEditing ? (
                      <>
                        <input
                          value={person.name}
                          onChange={(e) => {
                            const newPeople = [...editedPeople];
                            newPeople[idx] = { ...person, name: e.target.value };
                            setEditedPeople(newPeople);
                            markDirty();
                          }}
                          placeholder="Name"
                          className="flex-1 p-2 border border-gray-300 rounded text-sm"
                        />
                        <input
                          value={person.role}
                          onChange={(e) => {
                            const newPeople = [...editedPeople];
                            newPeople[idx] = { ...person, role: e.target.value };
                            setEditedPeople(newPeople);
                            markDirty();
                          }}
                          placeholder="Role"
                          className="w-32 p-2 border border-gray-300 rounded text-sm"
                        />
                        <button
                          onClick={() => {
                            setEditedPeople(editedPeople.filter((_, i) => i !== idx));
                            markDirty();
                          }}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </>
                    ) : (
                      <>
                        <span className="font-medium text-gray-900">{person.name}</span>
                        <span className="text-gray-500">-</span>
                        <span className="text-gray-600">{person.role}</span>
                      </>
                    )}
                  </div>
                ))}
                {isEditing && (
                  <button
                    onClick={() => {
                      setEditedPeople([...editedPeople, { name: '', role: '', confidence: 1.0 }]);
                      markDirty();
                    }}
                    className="flex items-center gap-1 text-blue-600 hover:text-blue-800 text-sm mt-2"
                  >
                    <Plus className="h-3 w-3" /> Add Person
                  </button>
                )}
              </EntitySection>

              {/* Dates Section */}
              <EntitySection
                title="Dates"
                icon={<Calendar className="h-5 w-5 text-green-500" />}
                expanded={expandedSections.dates}
                onToggle={() => toggleSection('dates')}
                count={editedDates.length}
                isEditing={isEditing}
                onStartEdit={() => setIsEditing(true)}
              >
                {editedDates.map((date, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    {isEditing ? (
                      <>
                        <input
                          value={date}
                          onChange={(e) => {
                            const newDates = [...editedDates];
                            newDates[idx] = e.target.value;
                            setEditedDates(newDates);
                            markDirty();
                          }}
                          className="flex-1 p-2 border border-gray-300 rounded text-sm"
                        />
                        <button
                          onClick={() => {
                            setEditedDates(editedDates.filter((_, i) => i !== idx));
                            markDirty();
                          }}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </>
                    ) : (
                      <span className="px-3 py-1 bg-green-50 text-green-700 rounded">{date}</span>
                    )}
                  </div>
                ))}
                {isEditing && (
                  <button
                    onClick={() => {
                      setEditedDates([...editedDates, '']);
                      markDirty();
                    }}
                    className="flex items-center gap-1 text-blue-600 hover:text-blue-800 text-sm mt-2"
                  >
                    <Plus className="h-3 w-3" /> Add Date
                  </button>
                )}
              </EntitySection>

              {/* Locations Section */}
              <EntitySection
                title="Locations"
                icon={<MapPin className="h-5 w-5 text-red-500" />}
                expanded={expandedSections.locations}
                onToggle={() => toggleSection('locations')}
                count={editedLocations.length}
                isEditing={isEditing}
                onStartEdit={() => setIsEditing(true)}
              >
                {editedLocations.map((location, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    {isEditing ? (
                      <>
                        <input
                          value={location}
                          onChange={(e) => {
                            const newLocations = [...editedLocations];
                            newLocations[idx] = e.target.value;
                            setEditedLocations(newLocations);
                            markDirty();
                          }}
                          className="flex-1 p-2 border border-gray-300 rounded text-sm"
                        />
                        <button
                          onClick={() => {
                            setEditedLocations(editedLocations.filter((_, i) => i !== idx));
                            markDirty();
                          }}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </>
                    ) : (
                      <span className="px-3 py-1 bg-red-50 text-red-700 rounded">{location}</span>
                    )}
                  </div>
                ))}
                {isEditing && (
                  <button
                    onClick={() => {
                      setEditedLocations([...editedLocations, '']);
                      markDirty();
                    }}
                    className="flex items-center gap-1 text-blue-600 hover:text-blue-800 text-sm mt-2"
                  >
                    <Plus className="h-3 w-3" /> Add Location
                  </button>
                )}
              </EntitySection>

              {/* Case Numbers Section */}
              <EntitySection
                title="Case Numbers"
                icon={<FileDigit className="h-5 w-5 text-orange-500" />}
                expanded={expandedSections.caseNumbers}
                onToggle={() => toggleSection('caseNumbers')}
                count={editedCaseNumbers.length}
                isEditing={isEditing}
                onStartEdit={() => setIsEditing(true)}
              >
                {editedCaseNumbers.map((caseNum, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    {isEditing ? (
                      <>
                        <input
                          value={caseNum}
                          onChange={(e) => {
                            const newCaseNums = [...editedCaseNumbers];
                            newCaseNums[idx] = e.target.value;
                            setEditedCaseNumbers(newCaseNums);
                            markDirty();
                          }}
                          className="flex-1 p-2 border border-gray-300 rounded text-sm"
                        />
                        <button
                          onClick={() => {
                            setEditedCaseNumbers(editedCaseNumbers.filter((_, i) => i !== idx));
                            markDirty();
                          }}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </>
                    ) : (
                      <span className="px-3 py-1 bg-orange-50 text-orange-700 rounded font-mono">
                        {caseNum}
                      </span>
                    )}
                  </div>
                ))}
                {isEditing && (
                  <button
                    onClick={() => {
                      setEditedCaseNumbers([...editedCaseNumbers, '']);
                      markDirty();
                    }}
                    className="flex items-center gap-1 text-blue-600 hover:text-blue-800 text-sm mt-2"
                  >
                    <Plus className="h-3 w-3" /> Add Case Number
                  </button>
                )}
              </EntitySection>

              {/* Organizations Section */}
              <EntitySection
                title="Organizations"
                icon={<Building className="h-5 w-5 text-indigo-500" />}
                expanded={expandedSections.organizations}
                onToggle={() => toggleSection('organizations')}
                count={editedOrganizations.length}
                isEditing={isEditing}
                onStartEdit={() => setIsEditing(true)}
              >
                {editedOrganizations.map((org, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    {isEditing ? (
                      <>
                        <input
                          value={org}
                          onChange={(e) => {
                            const newOrgs = [...editedOrganizations];
                            newOrgs[idx] = e.target.value;
                            setEditedOrganizations(newOrgs);
                            markDirty();
                          }}
                          className="flex-1 p-2 border border-gray-300 rounded text-sm"
                        />
                        <button
                          onClick={() => {
                            setEditedOrganizations(editedOrganizations.filter((_, i) => i !== idx));
                            markDirty();
                          }}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </>
                    ) : (
                      <span className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded">{org}</span>
                    )}
                  </div>
                ))}
                {isEditing && (
                  <button
                    onClick={() => {
                      setEditedOrganizations([...editedOrganizations, '']);
                      markDirty();
                    }}
                    className="flex items-center gap-1 text-blue-600 hover:text-blue-800 text-sm mt-2"
                  >
                    <Plus className="h-3 w-3" /> Add Organization
                  </button>
                )}
              </EntitySection>

              {/* Timeline Section */}
              {editedDates.length > 0 && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <button
                    onClick={() => toggleSection('timeline')}
                    className="flex items-center gap-2 w-full"
                  >
                    {expandedSections.timeline ? (
                      <ChevronDown className="h-5 w-5" />
                    ) : (
                      <ChevronRight className="h-5 w-5" />
                    )}
                    <Clock className="h-5 w-5 text-blue-500" />
                    <h3 className="text-lg font-semibold text-gray-900">Timeline</h3>
                  </button>

                  {expandedSections.timeline && (
                    <div className="mt-4">
                      <div className="relative">
                        {/* Timeline line */}
                        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-blue-200" />

                        {/* Timeline items */}
                        <div className="space-y-4">
                          {[...editedDates]
                            .sort((a, b) => new Date(a).getTime() - new Date(b).getTime())
                            .map((date, idx) => (
                              <div key={idx} className="relative flex items-center gap-4 pl-10">
                                {/* Timeline dot */}
                                <div className="absolute left-2.5 w-3 h-3 bg-blue-500 rounded-full border-2 border-white" />
                                {/* Date content */}
                                <div className="bg-white p-3 rounded-lg shadow-sm border border-gray-200 flex-1">
                                  <span className="font-medium text-gray-900">{date}</span>
                                </div>
                              </div>
                            ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Processing info */}
              {analysis.processing && (
                <div className="text-xs text-gray-500 pt-4 border-t border-gray-200">
                  <p>
                    Processed: {new Date(analysis.processing.started_at).toLocaleString()}
                    {analysis.processing.duration_ms && (
                      <span> ({(analysis.processing.duration_ms / 1000).toFixed(1)}s)</span>
                    )}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Click outside handler for export menu */}
      {showExportMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowExportMenu(false)}
        />
      )}
    </div>
  );
}

// Reusable Entity Section Component
interface EntitySectionProps {
  title: string;
  icon: React.ReactNode;
  expanded: boolean;
  onToggle: () => void;
  count: number;
  isEditing: boolean;
  onStartEdit: () => void;
  children: React.ReactNode;
}

function EntitySection({
  title,
  icon,
  expanded,
  onToggle,
  count,
  isEditing,
  onStartEdit,
  children
}: EntitySectionProps) {
  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full p-4"
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronRight className="h-5 w-5 text-gray-400" />
          )}
          {icon}
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
            {count}
          </span>
        </div>
        {!isEditing && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onStartEdit();
            }}
            className="text-gray-400 hover:text-gray-600"
          >
            <Pencil className="h-4 w-4" />
          </button>
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-2">
          {children}
        </div>
      )}
    </div>
  );
}
