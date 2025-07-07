// Suponiendo que usas d3.tree() para el layout:

const width = 900;
const height = 500;

const treeLayout = d3.tree().size([height, width - 160]); // Cambia el ancho y alto

// ...existing code...

// Cambia la proyección de los enlaces y nodos a horizontal:
const link = g.selectAll(".link")
    .data(root.links())
    .enter().append("path")
    .attr("class", "link")
    .attr("d", d3.linkHorizontal()
        .x(d => d.y) // y ahora es horizontal
        .y(d => d.x));

const node = g.selectAll(".node")
    .data(root.descendants())
    .enter().append("g")
    .attr("class", "node")
    .attr("transform", d => `translate(${d.y},${d.x})`);
// ...existing code...