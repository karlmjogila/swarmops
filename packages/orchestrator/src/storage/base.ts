/**
 * Base storage utilities for file-based JSON persistence
 */

import { promises as fs } from 'fs';
import * as path from 'path';

/**
 * Base class for JSON file storage
 */
export abstract class BaseStorage<T extends { id: string }> {
  protected filePath: string;
  protected cache: T[] | null = null;

  constructor(filePath: string) {
    this.filePath = filePath;
  }

  /**
   * Ensure the storage directory exists
   */
  protected async ensureDirectory(): Promise<void> {
    const dir = path.dirname(this.filePath);
    await fs.mkdir(dir, { recursive: true });
  }

  /**
   * Read data from storage file
   */
  protected async readData(): Promise<T[]> {
    if (this.cache !== null) {
      return this.cache;
    }

    try {
      await this.ensureDirectory();
      const content = await fs.readFile(this.filePath, 'utf-8');
      this.cache = JSON.parse(content) as T[];
      return this.cache;
    } catch (error: unknown) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        this.cache = [];
        return this.cache;
      }
      throw new StorageError(`Failed to read storage: ${(error as Error).message}`);
    }
  }

  /**
   * Write data to storage file (atomic write)
   */
  protected async writeData(data: T[]): Promise<void> {
    try {
      await this.ensureDirectory();
      const tempPath = `${this.filePath}.tmp`;
      const content = JSON.stringify(data, null, 2);
      
      // Atomic write: write to temp file, then rename
      await fs.writeFile(tempPath, content, 'utf-8');
      await fs.rename(tempPath, this.filePath);
      
      this.cache = data;
    } catch (error: unknown) {
      throw new StorageError(`Failed to write storage: ${(error as Error).message}`);
    }
  }

  /**
   * Invalidate the cache (force re-read on next access)
   */
  public invalidateCache(): void {
    this.cache = null;
  }

  /**
   * Get the storage file path
   */
  public getFilePath(): string {
    return this.filePath;
  }
}

/**
 * Custom error class for storage operations
 */
export class StorageError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'StorageError';
  }
}

/**
 * Error thrown when an item is not found
 */
export class NotFoundError extends Error {
  constructor(type: string, id: string) {
    super(`${type} not found: ${id}`);
    this.name = 'NotFoundError';
  }
}

/**
 * Error thrown when there's a conflict (e.g., duplicate name)
 */
export class ConflictError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConflictError';
  }
}

/**
 * Generate a UUID v4
 */
export function generateId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Get current ISO timestamp
 */
export function timestamp(): string {
  return new Date().toISOString();
}
