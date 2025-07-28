import pdfplumber
import json
from pathlib import Path
from collections import Counter
import re

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def deduplicate_repeating_chars(text):
    result = []
    i = 0
    while i < len(text):
        count = 1
        while i + count < len(text) and text[i + count] == text[i]:
            count += 1

        if count >= 3:
            result.append(text[i])
            i += count
        else:
            result.extend(text[i:i+count])
            i += count
    return ''.join(result)

def analyze_pdf_structure(pdf_path):
    try:
        doc = pdfplumber.open(pdf_path)
    except Exception as e:
        print(f"Error opening {pdf_path}: {e}")
        return "Error: Could not open document", []

    if not doc.pages:
        return "Error: Document has no pages", []

    blocks = []
    all_font_sizes = []

    for page_num, page in enumerate(doc.pages):
        lines = {}
        for char in page.chars:
            y0 = round(char['top'])
            lines.setdefault(y0, []).append(char)

        for y0, chars in sorted(lines.items()):
            chars.sort(key=lambda c: c['x0'])
            font_sizes = {round(c['size']) for c in chars}
            is_bolds = ["bold" in c['fontname'].lower() for c in chars]
            starts_bold_and_changes = len(is_bolds) > 1 and is_bolds[0] and not all(is_bolds)

            if len(font_sizes) > 1 or starts_bold_and_changes:
                continue

            line_text = clean_text("".join([c['text'] for c in chars]))
            line_text = deduplicate_repeating_chars(line_text)
            if not line_text:
                continue

            size = round(sum(c['size'] for c in chars) / len(chars))
            font = chars[0]['fontname']
            is_bold = all(is_bolds)
            x0 = chars[0]['x0']

            blocks.append({
                'text': line_text,
                'size': size,
                'font': font,
                'bold': is_bold,
                'page': page_num + 1,
                'y0': y0,
                'x0': x0
            })
            all_font_sizes.append(size)

    if not blocks:
        title = doc.metadata.get('Title', 'No text found in document')
        return title, []

    size_counts = Counter(all_font_sizes)
    body_size = size_counts.most_common(1)[0][0] if size_counts else 12

    heading_candidates = []
    for b in blocks:
        page_width = doc.pages[b['page'] - 1].width
        is_left_aligned = b['x0'] < page_width * 0.15
        starts_with_number = re.match(r'^\s*\d+', b['text'])
        is_style_heading = (
            b['bold'] and is_left_aligned and starts_with_number and len(b['text']) <= 100
        )
        if (b['size'] > body_size or is_style_heading) and \
           re.search(r'[a-zA-Z]', b['text']) and \
           not re.search(r'(https?://|www\\.|WWW\\.)', b['text']):
            heading_candidates.append(b)

    title_text = doc.metadata.get('Title', '')
    title_element = None
    height_threshold = doc.pages[0].height * 0.75
    first_page_candidates = [h for h in heading_candidates if h['page'] == 1 and h['y0'] < height_threshold]
    if first_page_candidates:
        max_size = max(h['size'] for h in first_page_candidates)
        for cand in sorted(first_page_candidates, key=lambda x: x['y0']):
            if cand['size'] == max_size:
                title_element = cand
                title_text = cand['text']
                break
    if not title_text and blocks:
        title_text = blocks[0]['text']

    structure_candidates_unfiltered = [h for h in heading_candidates if h != title_element]
    if title_element:
        structure_candidates_unfiltered = [
            h for h in structure_candidates_unfiltered
            if h['page'] > title_element['page'] or
               (h['page'] == title_element['page'] and h['y0'] > title_element['y0'])
        ]

    post_filter_candidates = []
    for h in structure_candidates_unfiltered:
        page = doc.pages[h['page'] - 1]
        in_header_footer = h['y0'] < page.height * 0.10 or h['y0'] > page.height * 0.90
        is_inside_table = False
        for table in page.find_tables():
            bbox = table.bbox
            if bbox[1] <= h['y0'] <= bbox[3]:
                blocks_in_box = [b for b in blocks if b['page'] == h['page'] and bbox[1] <= b['y0'] <= bbox[3]]
                if blocks_in_box:
                    blocks_in_box.sort(key=lambda b: b['y0'])
                    if h['y0'] > blocks_in_box[0]['y0']:
                        is_inside_table = True
                        break
        if not in_header_footer and not is_inside_table:
            post_filter_candidates.append(h)

    post_filter_candidates.sort(key=lambda x: (x['page'], x['y0']))

    pre_merged = []
    if post_filter_candidates:
        curr = dict(post_filter_candidates[0])
        curr['original_y0s'] = [curr['y0']]
        for next_cand in post_filter_candidates[1:]:
            same_page = next_cand['page'] == curr['page']
            size_close = abs(next_cand['size'] - curr['size']) <= 1
            vertical_gap = next_cand['y0'] - curr['y0']
            if same_page and size_close and vertical_gap <= curr['size'] * 1.5:
                curr['text'] += " " + next_cand['text']
                curr['y0'] = next_cand['y0']
                curr['original_y0s'].append(next_cand['y0'])
            else:
                pre_merged.append(curr)
                curr = dict(next_cand)
                curr['original_y0s'] = [curr['y0']]
        pre_merged.append(curr)

    centered_filtered = []
    i = 0
    while i < len(pre_merged):
        group = [pre_merged[i]]
        page_width = doc.pages[pre_merged[i]['page'] - 1].width
        center_margin = page_width * 0.15
        is_centered = lambda x: abs((x['x0'] + len(x['text'])*x['size']*0.4/2) - page_width / 2) < center_margin

        if not is_centered(pre_merged[i]):
            centered_filtered.append(pre_merged[i])
            i += 1
            continue

        j = i + 1
        while j < len(pre_merged) and pre_merged[j]['page'] == pre_merged[i]['page'] and is_centered(pre_merged[j]):
            group.append(pre_merged[j])
            j += 1

        if len(group) <= 2:
            centered_filtered.extend(group)
        else:
            group.sort(key=lambda x: x['size'], reverse=True)
            top_two = group[:2]
            top_two.sort(key=lambda x: x['y0'])
            centered_filtered.extend(top_two)
        i = j

    pre_merged = centered_filtered

    to_exclude = set()
    for i, h1 in enumerate(pre_merged):
        if len(h1['text']) >= 200:
            to_exclude.add(i)
            continue
        for j in range(i + 1, len(pre_merged)):
            h2 = pre_merged[j]
            if h1['page'] == h2['page']:
                for y1 in h1['original_y0s']:
                    for y2 in h2['original_y0s']:
                        if abs(y1 - y2) < 3 and h1['font'] != h2['font']:
                            to_exclude.add(i)
                            to_exclude.add(j)
                            break
                    if i in to_exclude:
                        break

    structure_candidates = [
        h for i, h in enumerate(pre_merged) if i not in to_exclude and not h['text'].strip().endswith(':')
    ]

    final_outline = []
    if structure_candidates:
        sizes = sorted({h['size'] for h in structure_candidates}, reverse=True)
        clusters = []
        i = 0
        while i < len(sizes):
            cluster = [sizes[i]]
            j = i + 1
            while j < len(sizes) and abs(sizes[j] - cluster[0]) <= 1:
                cluster.append(sizes[j])
                j += 1
            clusters.append(cluster)
            i = j

        size_to_level = {}
        for idx, cluster in enumerate(clusters):
            level = f"H{idx+1}"
            for sz in cluster:
                size_to_level[sz] = level

        for cand in structure_candidates:
            level = size_to_level.get(cand['size'])
            if level:
                final_outline.append({
                    "level": level,
                    "text": cand['text'],
                    "page": cand['page']
                })

    return clean_text(title_text), final_outline

def process_pdfs_in_directory():
    input_dir = Path("./input")
    output_dir = Path("./output")
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print("❌ No PDF files found in ./input.")
        return

    print(f"📄 Found {len(pdf_files)} PDF(s). Processing...")
    for pdf_file in pdf_files:
        print(f"→ {pdf_file.name}")
        title, outline = analyze_pdf_structure(pdf_file)
        result = {"title": title, "outline": outline}
        out_file = output_dir / f"{pdf_file.stem}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved to: {out_file.name}")

if __name__ == "__main__":
    process_pdfs_in_directory()
