import { sqliteTable, text, real } from 'drizzle-orm/sqlite-core';

export const projects = sqliteTable('projects', {
  id:        text('id').primaryKey(),
  name:      text('name').notNull(),
  color:     text('color').notNull().default('#6366f1'),
  columns:   text('columns').notNull(),  // JSON: ColumnDef[]
  tags:      text('tags').notNull(),     // JSON: Tag[]
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
});

export const cards = sqliteTable('cards', {
  id:          text('id').primaryKey(),
  projectId:   text('project_id').notNull().references(() => projects.id, { onDelete: 'cascade' }),
  columnId:    text('column_id').notNull(),
  title:       text('title').notNull(),
  description: text('description').notNull().default(''),
  position:    real('position').notNull(),
  tags:        text('tags').notNull(),       // JSON: Tag[]
  attributes:  text('attributes').notNull(), // JSON: CustomAttribute[]
  createdAt:   text('created_at').notNull(),
  updatedAt:   text('updated_at').notNull(),
});
