// Simple 8N1 UART transmitter for the laptop-only PM2.5 demo.
module uart_tx (
    clk,
    rst_n,
    tx_start,
    tx_data,
    tx,
    tx_busy,
    tx_done
);

parameter integer CLK_FREQ_HZ = 27000000;
parameter integer BAUD_RATE = 115200;
localparam integer CLKS_PER_BIT = CLK_FREQ_HZ / BAUD_RATE;

input clk;
input rst_n;
input tx_start;
input [7:0] tx_data;
output reg tx;
output reg tx_busy;
output reg tx_done;

localparam [1:0] STATE_IDLE = 2'd0;
localparam [1:0] STATE_START = 2'd1;
localparam [1:0] STATE_DATA = 2'd2;
localparam [1:0] STATE_STOP = 2'd3;

reg [1:0] state;
reg [15:0] clk_count;
reg [2:0] bit_index;
reg [7:0] data_shift;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        state <= STATE_IDLE;
        clk_count <= 16'd0;
        bit_index <= 3'd0;
        data_shift <= 8'd0;
        tx <= 1'b1;
        tx_busy <= 1'b0;
        tx_done <= 1'b0;
    end else begin
        tx_done <= 1'b0;

        case (state)
            STATE_IDLE: begin
                tx <= 1'b1;
                tx_busy <= 1'b0;
                clk_count <= 16'd0;
                bit_index <= 3'd0;
                if (tx_start) begin
                    data_shift <= tx_data;
                    tx_busy <= 1'b1;
                    state <= STATE_START;
                end
            end

            STATE_START: begin
                tx <= 1'b0;
                tx_busy <= 1'b1;
                if (clk_count == (CLKS_PER_BIT - 1)) begin
                    clk_count <= 16'd0;
                    state <= STATE_DATA;
                end else begin
                    clk_count <= clk_count + 16'd1;
                end
            end

            STATE_DATA: begin
                tx <= data_shift[bit_index];
                tx_busy <= 1'b1;
                if (clk_count == (CLKS_PER_BIT - 1)) begin
                    clk_count <= 16'd0;
                    if (bit_index == 3'd7) begin
                        bit_index <= 3'd0;
                        state <= STATE_STOP;
                    end else begin
                        bit_index <= bit_index + 3'd1;
                    end
                end else begin
                    clk_count <= clk_count + 16'd1;
                end
            end

            STATE_STOP: begin
                tx <= 1'b1;
                tx_busy <= 1'b1;
                if (clk_count == (CLKS_PER_BIT - 1)) begin
                    clk_count <= 16'd0;
                    tx_busy <= 1'b0;
                    tx_done <= 1'b1;
                    state <= STATE_IDLE;
                end else begin
                    clk_count <= clk_count + 16'd1;
                end
            end

            default: begin
                state <= STATE_IDLE;
            end
        endcase
    end
end

endmodule
