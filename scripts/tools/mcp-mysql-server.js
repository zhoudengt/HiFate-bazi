#!/usr/bin/env node
/**
 * MySQL MCP Server for HiFate-bazi Project
 * 
 * 为 Cursor AI 提供 MySQL 数据库访问能力
 * 用于规则查询、条件修改、数据分析等操作
 */

const mysql = require('mysql2/promise');
const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} = require('@modelcontextprotocol/sdk/types.js');

// MySQL 连接配置
const config = {
  host: process.env.MYSQL_HOST || '127.0.0.1',
  port: parseInt(process.env.MYSQL_PORT || '13306'),
  user: process.env.MYSQL_USER || 'root',
  password: process.env.MYSQL_PASSWORD || 'root',
  database: process.env.MYSQL_DATABASE || 'bazi_system',
  charset: process.env.CHARSET || 'utf8mb4',
  connectTimeout: 10000,
};

let connection = null;

// 初始化数据库连接
async function getConnection() {
  if (!connection) {
    connection = await mysql.createConnection(config);
  }
  return connection;
}

// 创建 MCP Server
const server = new Server(
  {
    name: 'mysql-bazi',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// 定义可用工具
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'query',
        description: '执行 SELECT 查询并返回结果',
        inputSchema: {
          type: 'object',
          properties: {
            sql: {
              type: 'string',
              description: 'SQL SELECT 查询语句',
            },
          },
          required: ['sql'],
        },
      },
      {
        name: 'execute',
        description: '执行 INSERT/UPDATE/DELETE 操作',
        inputSchema: {
          type: 'object',
          properties: {
            sql: {
              type: 'string',
              description: 'SQL DML 语句',
            },
            confirm: {
              type: 'boolean',
              description: '确认执行（必须为 true）',
            },
          },
          required: ['sql', 'confirm'],
        },
      },
      {
        name: 'get_rule',
        description: '查询指定规则编码的完整信息',
        inputSchema: {
          type: 'object',
          properties: {
            rule_code: {
              type: 'string',
              description: '规则编码，如 FORMULA_HEALTH_70012',
            },
          },
          required: ['rule_code'],
        },
      },
      {
        name: 'update_rule_condition',
        description: '更新规则的 conditions 字段',
        inputSchema: {
          type: 'object',
          properties: {
            rule_code: {
              type: 'string',
              description: '规则编码',
            },
            conditions: {
              type: 'object',
              description: '新的条件对象（JSON）',
            },
          },
          required: ['rule_code', 'conditions'],
        },
      },
      {
        name: 'list_rules',
        description: '列出指定类型的规则',
        inputSchema: {
          type: 'object',
          properties: {
            rule_type: {
              type: 'string',
              description: '规则类型，如 FORMULA_HEALTH',
            },
            limit: {
              type: 'number',
              description: '返回数量限制',
              default: 10,
            },
          },
          required: ['rule_type'],
        },
      },
      {
        name: 'check_encoding',
        description: '检查规则条件中的字符编码问题',
        inputSchema: {
          type: 'object',
          properties: {
            rule_type: {
              type: 'string',
              description: '规则类型，如 FORMULA_HEALTH',
            },
          },
          required: ['rule_type'],
        },
      },
    ],
  };
});

// 处理工具调用
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    const conn = await getConnection();

    switch (name) {
      case 'query': {
        const [rows] = await conn.query(args.sql);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(rows, null, 2),
            },
          ],
        };
      }

      case 'execute': {
        if (!args.confirm) {
          return {
            content: [
              {
                type: 'text',
                text: 'Error: 必须设置 confirm=true 才能执行修改操作',
              },
            ],
            isError: true,
          };
        }

        const [result] = await conn.query(args.sql);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(
                {
                  affectedRows: result.affectedRows,
                  insertId: result.insertId,
                  message: '执行成功',
                },
                null,
                2
              ),
            },
          ],
        };
      }

      case 'get_rule': {
        const [rows] = await conn.query(
          'SELECT * FROM bazi_rules WHERE rule_code = ?',
          [args.rule_code]
        );
        
        if (rows.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: `未找到规则: ${args.rule_code}`,
              },
            ],
          };
        }

        // 处理 JSON 字段
        const rule = rows[0];
        if (typeof rule.conditions === 'string') {
          try {
            // 修复字符编码问题
            let condStr = rule.conditions;
            try {
              condStr = Buffer.from(condStr, 'latin1').toString('utf8');
            } catch (e) {
              // 忽略编码转换错误
            }
            rule.conditions = JSON.parse(condStr);
          } catch (e) {
            rule.conditions_raw = rule.conditions;
            rule.conditions = null;
            rule.parse_error = e.message;
          }
        }

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(rule, null, 2),
            },
          ],
        };
      }

      case 'update_rule_condition': {
        const conditionsStr = JSON.stringify(args.conditions, null, 0).replace(
          /'/g,
          "\\'"
        );

        const [result] = await conn.query(
          `UPDATE bazi_rules SET conditions = ? WHERE rule_code = ?`,
          [conditionsStr, args.rule_code]
        );

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(
                {
                  affectedRows: result.affectedRows,
                  message: `规则 ${args.rule_code} 更新成功`,
                  new_conditions: args.conditions,
                },
                null,
                2
              ),
            },
          ],
        };
      }

      case 'list_rules': {
        const limit = args.limit || 10;
        const [rows] = await conn.query(
          'SELECT rule_code, rule_type, priority, enabled FROM bazi_rules WHERE rule_type = ? LIMIT ?',
          [args.rule_type, limit]
        );

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(rows, null, 2),
            },
          ],
        };
      }

      case 'check_encoding': {
        const [rows] = await conn.query(
          "SELECT rule_code, conditions FROM bazi_rules WHERE rule_type = ? AND conditions LIKE '%ç%'",
          [args.rule_type]
        );

        if (rows.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: `规则类型 ${args.rule_type} 没有发现字符编码问题`,
              },
            ],
          };
        }

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(
                {
                  message: '发现字符编码问题的规则',
                  count: rows.length,
                  rules: rows.map((r) => ({
                    rule_code: r.rule_code,
                    has_encoding_issue: true,
                  })),
                },
                null,
                2
              ),
            },
          ],
        };
      }

      default:
        return {
          content: [
            {
              type: 'text',
              text: `未知工具: ${name}`,
            },
          ],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}\nStack: ${error.stack}`,
        },
      ],
      isError: true,
    };
  }
});

// 启动服务器
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MySQL MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});

