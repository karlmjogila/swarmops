<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { get } from 'svelte/store';
  import {
    Button,
    Card,
    CardHeader,
    CardBody,
    CardFooter,
    Badge,
    Modal,
    ModalHeader,
    ModalBody,
    ModalFooter,
    Input,
  } from '$lib/components/ui';
  import { LoadingState, EmptyState } from '$lib/components/layout';
  import { api } from '$lib/api';
  import { auth } from '$lib/stores';
  import type { Content, ContentType, ContentStatus } from '@hl-bot/shared';

  // State
  let contents = $state<Content[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let filterStatus = $state<ContentStatus | 'all'>('all');
  let filterType = $state<ContentType | 'all'>('all');
  let sortBy = $state<'created' | 'updated' | 'title'>('updated');
  let sortOrder = $state<'asc' | 'desc'>('desc');
  
  // Upload modal state
  let uploadModalOpen = $state(false);
  let uploadType = $state<ContentType>('youtube');
  let uploadUrl = $state('');
  let uploadText = $state('');
  let uploadTitle = $state('');
  let uploadDescription = $state('');
  let uploading = $state(false);
  let uploadError = $state<string | null>(null);
  
  // Details modal state
  let selectedContent = $state<Content | null>(null);
  let detailsModalOpen = $state(false);
  
  // Delete confirmation
  let deleteConfirmOpen = $state(false);
  let contentToDelete = $state<Content | null>(null);
  
  // Auto-refresh for processing content
  let refreshInterval: ReturnType<typeof setInterval> | null = null;

  // Computed filtered and sorted content
  let filteredContents = $derived(() => {
    let result = contents;
    
    // Filter by status
    if (filterStatus !== 'all') {
      result = result.filter(c => c.status === filterStatus);
    }
    
    // Filter by type
    if (filterType !== 'all') {
      result = result.filter(c => c.type === filterType);
    }
    
    // Sort
    result = [...result].sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'title':
          comparison = (a.metadata.title || '').localeCompare(b.metadata.title || '');
          break;
        case 'created':
          comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
          break;
        case 'updated':
          comparison = new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
          break;
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });
    
    return result;
  });

  // Check if any content is processing
  let hasProcessingContent = $derived(() => {
    return contents.some(c => c.status === 'downloading' || c.status === 'processing');
  });

  // Load content items
  async function loadContents() {
    loading = true;
    error = null;
    
    try {
      const response = await api.content.list();
      contents = response.data;
    } catch (err) {
      console.error('Failed to load content:', err);
      error = err instanceof Error ? err.message : 'Failed to load content';
    } finally {
      loading = false;
    }
  }

  // Upload new content
  async function handleUpload() {
    if (!uploadUrl && !uploadText) {
      uploadError = 'Please provide a URL or text';
      return;
    }
    
    uploading = true;
    uploadError = null;
    
    try {
      const authState = get(auth);
      if (!authState.user) {
        uploadError = 'You must be logged in to upload content';
        return;
      }
      
      const input: any = {
        userId: authState.user.id,
        type: uploadType,
        metadata: {
          title: uploadTitle || undefined,
          description: uploadDescription || undefined,
        },
      };
      
      if (uploadType === 'youtube' || uploadType === 'url') {
        if (!uploadUrl) {
          uploadError = 'URL is required';
          return;
        }
        input.sourceUrl = uploadUrl;
      } else if (uploadType === 'text') {
        input.artifacts = { text: uploadText };
      }
      
      await api.content.create(input);
      await loadContents();
      
      // Reset form
      uploadModalOpen = false;
      uploadUrl = '';
      uploadText = '';
      uploadTitle = '';
      uploadDescription = '';
      uploadType = 'youtube';
    } catch (err) {
      console.error('Failed to upload content:', err);
      uploadError = err instanceof Error ? err.message : 'Failed to upload content';
    } finally {
      uploading = false;
    }
  }

  // Retry failed content
  async function retryContent(content: Content) {
    try {
      await api.content.retry(content.id);
      await loadContents();
    } catch (err) {
      console.error('Failed to retry content:', err);
      alert('Failed to retry content');
    }
  }

  // Delete content
  async function deleteContent(content: Content) {
    try {
      await api.content.delete(content.id);
      await loadContents();
      deleteConfirmOpen = false;
      contentToDelete = null;
    } catch (err) {
      console.error('Failed to delete content:', err);
      alert('Failed to delete content');
    }
  }

  function openDetails(content: Content) {
    selectedContent = content;
    detailsModalOpen = true;
  }

  function openDeleteConfirm(content: Content) {
    contentToDelete = content;
    deleteConfirmOpen = true;
  }

  function openUploadModal() {
    uploadModalOpen = true;
    uploadError = null;
  }

  // Status badge variant mapping
  function getStatusBadgeVariant(status: ContentStatus): 'success' | 'warning' | 'error' | 'info' | 'default' {
    switch (status) {
      case 'completed':
        return 'success';
      case 'pending':
        return 'info';
      case 'downloading':
      case 'processing':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  }

  // Type badge color
  function getTypeBadgeVariant(type: ContentType): 'success' | 'warning' | 'error' | 'info' | 'default' {
    switch (type) {
      case 'youtube':
        return 'error'; // red like YouTube
      case 'pdf':
        return 'info';
      case 'image':
        return 'warning';
      case 'text':
        return 'default';
      case 'url':
        return 'info';
      default:
        return 'default';
    }
  }

  // Format date
  function formatDate(date: Date | string): string {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  // Format duration
  function formatDuration(seconds?: number): string {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  // Format file size
  function formatFileSize(bytes?: number): string {
    if (!bytes) return 'N/A';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  }

  // Get icon for content type
  function getTypeIcon(type: ContentType): string {
    switch (type) {
      case 'youtube':
        return '📹';
      case 'pdf':
        return '📄';
      case 'image':
        return '🖼️';
      case 'text':
        return '📝';
      case 'url':
        return '🔗';
      default:
        return '📦';
    }
  }

  // Setup auto-refresh for processing content
  onMount(() => {
    loadContents();
    
    // Auto-refresh every 5 seconds if there's processing content
    refreshInterval = setInterval(() => {
      if (hasProcessingContent()) {
        loadContents();
      }
    }, 5000);
  });

  onDestroy(() => {
    if (refreshInterval) {
      clearInterval(refreshInterval);
    }
  });
</script>

<div class="container mx-auto p-6 space-y-6">
  <!-- Header -->
  <div class="flex justify-between items-center">
    <div>
      <h1 class="text-3xl font-bold text-text-primary">Content Ingestion</h1>
      <p class="text-text-secondary mt-1">Upload and process trading content for strategy extraction</p>
    </div>
    <Button variant="primary" onclick={openUploadModal}>
      Upload Content
    </Button>
  </div>

  <!-- Filters -->
  <Card>
    <CardBody>
      <div class="flex flex-wrap gap-4 items-center">
        <div class="flex-1 min-w-[200px]">
          <label for="filter-status" class="block text-sm font-medium text-text-primary mb-1">Filter by Status</label>
          <select
            id="filter-status"
            bind:value={filterStatus}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="downloading">Downloading</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        <div class="flex-1 min-w-[200px]">
          <label for="filter-type" class="block text-sm font-medium text-text-primary mb-1">Filter by Type</label>
          <select
            id="filter-type"
            bind:value={filterType}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Types</option>
            <option value="youtube">YouTube</option>
            <option value="pdf">PDF</option>
            <option value="image">Image</option>
            <option value="text">Text</option>
            <option value="url">URL</option>
          </select>
        </div>

        <div class="flex-1 min-w-[200px]">
          <label for="sort-by" class="block text-sm font-medium text-text-primary mb-1">Sort By</label>
          <select
            id="sort-by"
            bind:value={sortBy}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="updated">Last Updated</option>
            <option value="created">Date Created</option>
            <option value="title">Title</option>
          </select>
        </div>

        <div class="flex-1 min-w-[200px]">
          <label for="sort-order" class="block text-sm font-medium text-text-primary mb-1">Order</label>
          <select
            id="sort-order"
            bind:value={sortOrder}
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>

        <div class="flex items-end">
          <Button variant="secondary" onclick={loadContents}>
            Refresh
          </Button>
        </div>
      </div>
    </CardBody>
  </Card>

  <!-- Content Grid -->
  {#if loading}
    <div class="flex justify-center items-center py-12">
      <LoadingState type="spinner" size="lg" />
    </div>
  {:else if error}
    <Card>
      <CardBody>
        <div class="text-center py-8">
          <p class="text-error-600 text-lg mb-4">Error loading content</p>
          <p class="text-text-secondary mb-4">{error}</p>
          <Button variant="primary" onclick={loadContents}>Try Again</Button>
        </div>
      </CardBody>
    </Card>
  {:else if filteredContents().length === 0}
    <Card>
      <CardBody>
        <EmptyState
          title="No content found"
          description={filterStatus === 'all' && filterType === 'all'
            ? "Get started by uploading your first trading content."
            : "No content matches the selected filters."}
          action={{
            label: 'Upload Content',
            onClick: openUploadModal,
          }}
        />
      </CardBody>
    </Card>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {#each filteredContents() as content (content.id)}
        <Card>
          <CardHeader>
            <div class="flex justify-between items-start gap-2">
              <div class="flex items-center gap-2 flex-1 min-w-0">
                <span class="text-2xl flex-shrink-0">{getTypeIcon(content.type)}</span>
                <h3 class="text-lg font-semibold text-text-primary truncate">
                  {content.metadata.title || 'Untitled'}
                </h3>
              </div>
              <div class="flex gap-1 flex-shrink-0">
                <Badge variant={getTypeBadgeVariant(content.type)}>
                  {content.type}
                </Badge>
                <Badge variant={getStatusBadgeVariant(content.status)}>
                  {content.status}
                </Badge>
              </div>
            </div>
          </CardHeader>
          
          <CardBody>
            {#if content.metadata.description}
              <p class="text-text-secondary text-sm mb-4 line-clamp-3">
                {content.metadata.description}
              </p>
            {/if}
            
            <!-- Progress bar for processing content -->
            {#if (content.status === 'downloading' || content.status === 'processing') && content.progress !== undefined}
              <div class="mb-4">
                <div class="flex justify-between text-xs text-text-secondary mb-1">
                  <span>{content.status === 'downloading' ? 'Downloading' : 'Processing'}</span>
                  <span>{content.progress}%</span>
                </div>
                <div class="w-full bg-bg-secondary rounded-full h-2">
                  <div
                    class="bg-primary-500 h-2 rounded-full transition-all duration-300"
                    style="width: {content.progress}%"
                  ></div>
                </div>
              </div>
            {/if}
            
            <!-- Error message -->
            {#if content.status === 'failed' && content.error}
              <div class="mb-4 p-2 bg-error-50 border border-error-200 rounded text-sm text-error-700">
                {content.error}
              </div>
            {/if}
            
            <div class="space-y-2 text-sm">
              {#if content.metadata.author}
                <div class="flex justify-between">
                  <span class="text-text-secondary">Author:</span>
                  <span class="text-text-primary font-medium truncate ml-2">
                    {content.metadata.author}
                  </span>
                </div>
              {/if}
              
              {#if content.metadata.duration}
                <div class="flex justify-between">
                  <span class="text-text-secondary">Duration:</span>
                  <span class="text-text-primary font-medium">
                    {formatDuration(content.metadata.duration)}
                  </span>
                </div>
              {/if}
              
              {#if content.metadata.fileSize}
                <div class="flex justify-between">
                  <span class="text-text-secondary">Size:</span>
                  <span class="text-text-primary font-medium">
                    {formatFileSize(content.metadata.fileSize)}
                  </span>
                </div>
              {/if}
              
              {#if content.sourceUrl}
                <div class="flex justify-between">
                  <span class="text-text-secondary">Source:</span>
                  <a
                    href={content.sourceUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-primary-600 hover:text-primary-700 font-medium truncate ml-2 max-w-[200px]"
                  >
                    View
                  </a>
                </div>
              {/if}
              
              <div class="flex justify-between text-xs pt-2 border-t border-border">
                <span class="text-text-secondary">Updated:</span>
                <span class="text-text-primary">
                  {formatDate(content.updatedAt)}
                </span>
              </div>
            </div>
          </CardBody>
          
          <CardFooter>
            <div class="flex gap-2 flex-wrap">
              <Button
                size="sm"
                variant="outline"
                onclick={() => openDetails(content)}
              >
                Details
              </Button>
              
              {#if content.status === 'failed'}
                <Button
                  size="sm"
                  variant="warning"
                  onclick={() => retryContent(content)}
                >
                  Retry
                </Button>
              {/if}
              
              {#if content.status === 'completed' && content.artifacts.transcript}
                <Button
                  size="sm"
                  variant="success"
                  onclick={() => alert('Generate strategy coming soon')}
                >
                  Generate Strategy
                </Button>
              {/if}
              
              <Button
                size="sm"
                variant="danger"
                onclick={() => openDeleteConfirm(content)}
              >
                Delete
              </Button>
            </div>
          </CardFooter>
        </Card>
      {/each}
    </div>
  {/if}
</div>

<!-- Upload Modal -->
<Modal bind:open={uploadModalOpen} title="Upload Content" size="lg">
  <ModalBody>
    <div class="space-y-4">
      <!-- Content Type Selector -->
      <div>
        <label for="upload-type" class="block text-sm font-medium text-text-primary mb-2">
          Content Type
        </label>
        <select
          id="upload-type"
          bind:value={uploadType}
          class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="youtube">YouTube Video</option>
          <option value="url">Web URL</option>
          <option value="text">Text Content</option>
          <option value="pdf">PDF (coming soon)</option>
          <option value="image">Image (coming soon)</option>
        </select>
      </div>

      <!-- URL Input for YouTube/URL -->
      {#if uploadType === 'youtube' || uploadType === 'url'}
        <Input
          label={uploadType === 'youtube' ? 'YouTube URL' : 'Web URL'}
          placeholder={uploadType === 'youtube' 
            ? 'https://youtube.com/watch?v=...' 
            : 'https://example.com/article'}
          bind:value={uploadUrl}
          required
        />
      {/if}

      <!-- Text Input for Text Content -->
      {#if uploadType === 'text'}
        <div>
          <label for="upload-text" class="block text-sm font-medium text-text-primary mb-2">
            Text Content
          </label>
          <textarea
            id="upload-text"
            bind:value={uploadText}
            rows="8"
            placeholder="Paste your trading strategy or analysis here..."
            class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500 resize-y"
          ></textarea>
        </div>
      {/if}

      <!-- Optional Metadata -->
      <Input
        label="Title (optional)"
        placeholder="Give this content a descriptive title"
        bind:value={uploadTitle}
      />

      <div>
        <label for="upload-description" class="block text-sm font-medium text-text-primary mb-2">
          Description (optional)
        </label>
        <textarea
          id="upload-description"
          bind:value={uploadDescription}
          rows="3"
          placeholder="Add any notes or context about this content..."
          class="w-full px-3 py-2 border border-border rounded-md bg-bg-primary text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-500 resize-y"
        ></textarea>
      </div>

      {#if uploadError}
        <div class="p-3 bg-error-50 border border-error-200 rounded text-sm text-error-700">
          {uploadError}
        </div>
      {/if}

      {#if uploadType === 'pdf' || uploadType === 'image'}
        <div class="p-4 bg-warning-50 border border-warning-200 rounded text-sm text-warning-800">
          <strong>Coming Soon:</strong> {uploadType === 'pdf' ? 'PDF' : 'Image'} upload is not yet implemented.
        </div>
      {/if}
    </div>
  </ModalBody>
  <ModalFooter>
    <Button
      variant="secondary"
      onclick={() => { uploadModalOpen = false; uploadError = null; }}
      disabled={uploading}
    >
      Cancel
    </Button>
    <Button
      variant="primary"
      onclick={handleUpload}
      disabled={uploading || uploadType === 'pdf' || uploadType === 'image'}
    >
      {uploading ? 'Uploading...' : 'Upload'}
    </Button>
  </ModalFooter>
</Modal>

<!-- Content Details Modal -->
{#if selectedContent}
  <Modal bind:open={detailsModalOpen} title={selectedContent.metadata.title || 'Content Details'} size="xl">
    <ModalBody>
      <div class="space-y-4">
        <!-- Status and Type -->
        <div class="flex gap-4">
          <div class="flex-1">
            <h4 class="text-sm font-semibold text-text-primary mb-1">Status</h4>
            <Badge variant={getStatusBadgeVariant(selectedContent.status)}>
              {selectedContent.status}
            </Badge>
          </div>
          <div class="flex-1">
            <h4 class="text-sm font-semibold text-text-primary mb-1">Type</h4>
            <Badge variant={getTypeBadgeVariant(selectedContent.type)}>
              {selectedContent.type}
            </Badge>
          </div>
        </div>

        <!-- Metadata -->
        {#if selectedContent.metadata.description}
          <div>
            <h4 class="text-sm font-semibold text-text-primary mb-1">Description</h4>
            <p class="text-text-secondary text-sm">{selectedContent.metadata.description}</p>
          </div>
        {/if}

        <div class="grid grid-cols-2 gap-4">
          {#if selectedContent.metadata.author}
            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Author</h4>
              <p class="text-text-secondary text-sm">{selectedContent.metadata.author}</p>
            </div>
          {/if}

          {#if selectedContent.metadata.duration}
            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Duration</h4>
              <p class="text-text-secondary text-sm">{formatDuration(selectedContent.metadata.duration)}</p>
            </div>
          {/if}

          {#if selectedContent.metadata.fileSize}
            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">File Size</h4>
              <p class="text-text-secondary text-sm">{formatFileSize(selectedContent.metadata.fileSize)}</p>
            </div>
          {/if}

          {#if selectedContent.metadata.publishedAt}
            <div>
              <h4 class="text-sm font-semibold text-text-primary mb-1">Published</h4>
              <p class="text-text-secondary text-sm">{formatDate(selectedContent.metadata.publishedAt)}</p>
            </div>
          {/if}
        </div>

        {#if selectedContent.sourceUrl}
          <div>
            <h4 class="text-sm font-semibold text-text-primary mb-1">Source URL</h4>
            <a
              href={selectedContent.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              class="text-primary-600 hover:text-primary-700 text-sm break-all"
            >
              {selectedContent.sourceUrl}
            </a>
          </div>
        {/if}

        <!-- Artifacts -->
        {#if selectedContent.artifacts.transcript}
          <div>
            <h4 class="text-sm font-semibold text-text-primary mb-2">Transcript</h4>
            <div class="max-h-64 overflow-y-auto p-3 bg-bg-secondary rounded border border-border">
              <p class="text-text-secondary text-sm whitespace-pre-wrap">
                {selectedContent.artifacts.transcript}
              </p>
            </div>
          </div>
        {/if}

        {#if selectedContent.artifacts.text}
          <div>
            <h4 class="text-sm font-semibold text-text-primary mb-2">Text Content</h4>
            <div class="max-h-64 overflow-y-auto p-3 bg-bg-secondary rounded border border-border">
              <p class="text-text-secondary text-sm whitespace-pre-wrap">
                {selectedContent.artifacts.text}
              </p>
            </div>
          </div>
        {/if}

        {#if selectedContent.artifacts.images && selectedContent.artifacts.images.length > 0}
          <div>
            <h4 class="text-sm font-semibold text-text-primary mb-2">Images ({selectedContent.artifacts.images.length})</h4>
            <div class="grid grid-cols-2 gap-2">
              {#each selectedContent.artifacts.images.slice(0, 4) as image}
                <img src={image} alt="Content artifact" class="rounded border border-border" />
              {/each}
            </div>
          </div>
        {/if}

        <!-- Error -->
        {#if selectedContent.status === 'failed' && selectedContent.error}
          <div>
            <h4 class="text-sm font-semibold text-error-600 mb-2">Error</h4>
            <div class="p-3 bg-error-50 border border-error-200 rounded">
              <p class="text-error-700 text-sm">{selectedContent.error}</p>
            </div>
          </div>
        {/if}

        <!-- Timestamps -->
        <div class="grid grid-cols-3 gap-4 pt-4 border-t border-border text-xs">
          <div>
            <span class="text-text-secondary">Created:</span>
            <p class="text-text-primary">{formatDate(selectedContent.createdAt)}</p>
          </div>
          <div>
            <span class="text-text-secondary">Updated:</span>
            <p class="text-text-primary">{formatDate(selectedContent.updatedAt)}</p>
          </div>
          {#if selectedContent.completedAt}
            <div>
              <span class="text-text-secondary">Completed:</span>
              <p class="text-text-primary">{formatDate(selectedContent.completedAt)}</p>
            </div>
          {/if}
        </div>
      </div>
    </ModalBody>
    <ModalFooter>
      <Button variant="secondary" onclick={() => detailsModalOpen = false}>Close</Button>
      {#if selectedContent.status === 'failed'}
        <Button variant="warning" onclick={() => { retryContent(selectedContent!); detailsModalOpen = false; }}>
          Retry
        </Button>
      {/if}
    </ModalFooter>
  </Modal>
{/if}

<!-- Delete Confirmation Modal -->
{#if contentToDelete}
  <Modal bind:open={deleteConfirmOpen} title="Delete Content">
    <ModalBody>
      <p class="text-text-secondary">
        Are you sure you want to delete <strong>{contentToDelete.metadata.title || 'this content'}</strong>?
        This action cannot be undone.
      </p>
    </ModalBody>
    <ModalFooter>
      <Button variant="secondary" onclick={() => deleteConfirmOpen = false}>Cancel</Button>
      <Button variant="danger" onclick={() => deleteContent(contentToDelete!)}>Delete</Button>
    </ModalFooter>
  </Modal>
{/if}

<style>
  .line-clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
